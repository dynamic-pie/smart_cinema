from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from core.serializers import UserSerializer, MovieSerializer
from rest_framework.renderers import JSONRenderer
import random

from django.contrib.auth import authenticate
from core.models import Ratings, Movie, Session, Hall
from django.db import connection

import numpy as np
import json
from datetime import datetime

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
            if ratings[user_id][movie_id] == 0 and rate >= 2:
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

    def get_popular_films(self):
        query = 'select movie_id, AVG(rating) as avg_rate from core_ratings group by movie_id order by AVG(rating) DESC;'
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        rows = rows[0:1000]
        rand_list = random.sample(rows, 50)
        popular_films = []
        for film in rand_list:
            popular_films.append(int(film[0]))

        return popular_films

    def get(self, request, format=None):
        r = request.auth
        user = request.user

        old_movie_ids = []

        ratings, movie_new_indexes, rev_movie_new_indexes, user_new_indexes, rev_user_new_indexes = self.get_ratings(
            user.id, 10)

        popular_films = self.get_popular_films()

        if len(ratings) != 0:
            user_similarity = self.fast_similarity(ratings)
            user_pred = self.predict_topk(ratings, user_similarity, user_new_indexes[user.id])
            movie_ids = self.get_best_films(ratings, user_pred, user_new_indexes[user.id])
            for movie_id in movie_ids:
                old_movie_ids.append(rev_movie_new_indexes[movie_id[0]])

        if len(old_movie_ids) < 20:
            for i in range(50 - len(old_movie_ids)):
                old_movie_ids.append(popular_films[i])

        old_movie_ids = old_movie_ids[0:20]

        movies = []

        for i in old_movie_ids:
            movies.append(MovieSerializer(Movie.objects.get(id=i)).data)

        content = {
            'movies': movies
        }

        return Response(content)


class SetMark(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        mark = self.request.query_params.get('mark', None)
        movie_id = self.request.query_params.get('movie_id', None)

        query = 'INSERT INTO core_ratings (rating, timestamp, movie_id, user_id) ' \
                'VALUES ({}, \'{}\', \'{}\', {})'.format(mark, str(datetime.date(datetime.now())), movie_id, user.id)

        with connection.cursor() as cursor:
            cursor.execute(query)

        content = {
            'status': 'ok'
        }

        return Response(content)


class GetMovies(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_popular_films(self):
        query = 'select movie_id, AVG(rating) as avg_rate from core_ratings group by movie_id order by AVG(rating) DESC;'
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        rows = rows[0:1000]
        rand_list = random.sample(rows, 50)
        popular_films = []
        for film in rand_list:
            popular_films.append(int(film[0]))

        return popular_films

    def get(self, request, format=None):
        popular_films = self.get_popular_films()
        movies = []

        for i in popular_films:
            movies.append(MovieSerializer(Movie.objects.get(id=i)).data)

        content = {
            'movies': movies
        }

        return Response(content)


class GetSessions(APIView):
    def get(self, request, format=None):
        sessions = Session.objects.all()
        sessions_id = []
        for session in sessions:
            sessions_id.append({
                'movie_id': session.movie_id,
                'session_id': session.id
            })

        movies = []
        for i in sessions_id:
            movies.append(
                {
                    'movie': MovieSerializer(Movie.objects.get(id=i['movie_id'])).data,
                    'session_id': i['session_id']
                }
            )

        content = {
            'movies': movies
        }

        return Response(content)


class BuyTicket(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        user_id = request.user.id
        session_id = self.request.query_params.get('session_id', None)
        row = self.request.query_params.get('x', None)
        column = self.request.query_params.get('y', None)

        query1 = 'INSERT INTO core_place (row_number, column_number, session_id) VALUES ({}, {}, {})'.format(row, column, session_id)
        with connection.cursor() as cursor:
            cursor.execute(query1)

        content = {
            'status': 'ok'
        }

        return Response(content)


class GetSessionInfo(APIView):
    def get(self, request, format=None):
        user_id = request.user.id
        session_id = self.request.query_params.get('session_id', None)

        query1 = 'SELECT row_number, column_number FROM core_place WHERE session_id = {}'.format(session_id)

        places = []
        with connection.cursor() as cursor:
            cursor.execute(query1)
            rows = cursor.fetchall()

        max_column = Session.objects.get(id=session_id).hall.column_count
        max_row = Session.objects.get(id=session_id).hall.row_count

        for row in rows:
            places.append(
                {
                    'x': int(row[0]),
                    'y': int(row[1])
                }
            )

        content = {
            'busy': places,
            'max_y': max_column,
            'max_x': max_row
        }

        return Response(content)