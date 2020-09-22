from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.models import User
from .models import Movie


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(min_length=8)

    is_superuser = serializers.BooleanField()

    def create(self, validated_data):
        if validated_data['is_superuser']:
            user = User.objects.create_superuser(validated_data['username'], validated_data['email'],
                                                 validated_data['password'])
        else:
            user = User.objects.create_user(validated_data['username'], validated_data['email'],
                                            validated_data['password'])
        return user

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'is_superuser')


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ('id', 'title', 'release_date', 'in_cinema', 'image_link', 'imdb_id', 'summary')

