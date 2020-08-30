from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Movie(models.Model):
    title = models.CharField(max_length=200)
    release_date = models.DateField()
    in_cinema = models.BooleanField(default=False, blank=True, null=True)
    image_link = models.URLField(default=None, blank=True, null=True)
    imdb_id = models.CharField(max_length=8, default=None, blank=True, null=True)
    summary = models.TextField()


class Ratings(models.Model):
    rating = models.SmallIntegerField()
    timestamp = models.DateTimeField()
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class Genre(models.Model):
    genre_name = models.CharField(max_length=100)


class MovieGenre(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)


class Hall(models.Model):
    title = models.CharField(max_length=100)
    row_count = models.SmallIntegerField()
    column_count = models.SmallIntegerField()
    summary = models.TextField()


class Place(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    row_number = models.SmallIntegerField()
    column_number = models.SmallIntegerField()


class Session(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    release_date = models.DateTimeField()


class Ticket(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    status = models.BooleanField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ManyToManyField(Session)


class Poster(models.Model):
    movie_id = models.IntegerField(default=None)
    imdb_id = models.CharField(max_length=8, default=None, blank=True, null=True)
    poster_url = models.URLField()
