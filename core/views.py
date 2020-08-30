from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from core.serializers import UserSerializer, MovieSerializer

from django.contrib.auth import authenticate
from core.models import Ratings, Movie
from django.db import connection

import numpy as np
import json

rating_model_cache = len(Ratings.objects.all())


class GetMovie(RetrieveAPIView):
    queryset = Movie.objects.all()
    lookup_fields = ['movie_id']
    serializer_class = MovieSerializer


class UserCreate(APIView):
    def post(self, request, format='json'):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if user:
                token = Token.objects.create(user=user)
                json = serializer.data
                json['token'] = token.key
                return Response(json, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = ()

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            return Response({"token": user.auth_token.key})
        else:
            return Response({"error": "Wrong Credentials"}, status=status.HTTP_400_BAD_REQUEST)


class GetRecommendation(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_ratings(self, user_id, cnt):
        query = 'select user_id, movie_id, rating from core_ratings where user_id in ' \
                '(select userTable.id from auth_user as userTable ' \
                'where exists ( select cnt from (select count(1) as cnt ' \
                'from (select movie_id from core_ratings as A ' \
                'where A.user_id = userTable.id intersect ' \
                'select movie_id from core_ratings as B ' \
                'where B.user_id = {}) as subquery) as subquery where cnt > {}));'.format(user_id, cnt)

        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        movie_new_indexes = {}
        rev_movie_new_indexes = {}

        user_new_indexes = {}
        rev_user_new_indexes = {}

        index = 0
        user_index = 0
        for row in rows:
            if row[1] not in movie_new_indexes:
                movie_new_indexes[row[1]] = index
                rev_movie_new_indexes[index] = row[1]
                index += 1

            if row[0] not in user_new_indexes:
                user_new_indexes[row[0]] = user_index
                rev_user_new_indexes[user_index] = row[0]
                user_index += 1

        ratings = np.zeros((user_index, index))

        for row in rows:
            ratings[user_new_indexes[row[0]], movie_new_indexes[row[1]]] = row[2]

        return ratings, movie_new_indexes, rev_movie_new_indexes, user_new_indexes, rev_user_new_indexes

    def item_shape(self):
        with connection.cursor() as cursor:
            cursor.execute('select max(t.id) from core_movie as t;')
            row = cursor.fetchone()

        return row[0]

    def fast_similarity(self, ratings, epsilon=1e-9):
        print(ratings.shape)
        sim = ratings.dot(ratings.T) + epsilon
        norms = np.array([np.sqrt(np.diagonal(sim))])
        return sim / norms / norms.T

    def predict_fast_simple(self, ratings, similarity):
        return similarity.dot(ratings) / np.array([np.abs(similarity).sum(axis=1)]).T

    def get_best_films(self, ratings, pred, user_id):
        not_watched = {}

        movie_id = 0
        for rate in pred:
            if ratings[user_id][movie_id] == 0 and rate > 3:
                not_watched[movie_id] = rate
            movie_id += 1

        result = sorted(not_watched.items(), key=lambda item: item[1], reverse=True)

        return result

    def predict_topk(self, ratings, similarity, user_id, k=40):
        pred = np.zeros(ratings.shape[1])
        top_k_users = [np.argsort(similarity[:, user_id])[:-k - 1:-1]]
        for j in range(ratings.shape[1]):
            pred[j] = similarity[user_id, :][top_k_users].dot(ratings[:, j][top_k_users])
            pred[j] /= np.sum(np.abs(similarity[user_id, :][top_k_users]))
        return pred

    def get(self, request, format=None):
        r = request.auth
        user = request.user

        ratings, movie_new_indexes, rev_movie_new_indexes, user_new_indexes, rev_user_new_indexes = self.get_ratings(
            user.id, 10)

        user_similarity = self.fast_similarity(ratings)

        user_pred = self.predict_topk(ratings, user_similarity, user_new_indexes[user.id])

        movie_ids = self.get_best_films(ratings, user_pred, user_new_indexes[user.id])

        old_movie_ids = []
        for movie_id in movie_ids:
            old_movie_ids.append(rev_movie_new_indexes[movie_id[0]])

        old_movie_ids = old_movie_ids[0:50]

        content = {
            'movie_ids': json.dumps(old_movie_ids)
        }
        return Response(content)
