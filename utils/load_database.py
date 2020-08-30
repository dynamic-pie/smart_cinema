import psycopg2
import random
import string
import os
import pandas as pd
import math
import requests
from time import sleep


def insert_genre(genre_name, cursor):
    query = 'INSERT INTO core_genre (genre_name) VALUES (\'{}\')'.format(genre_name)
    cursor.execute(query)


def insert_ratings(rating, timestamp, movie_id, user_id, cursor):
    query = 'INSERT INTO core_ratings (rating, timestamp, movie_id, user_id) ' \
            'VALUES ({}, \'{}\', \'{}\', {})'.format(rating, timestamp, movie_id, user_id)
    cursor.execute(query)


def insert_moviegenre(movie_id, genre_id, cursor):
    query = 'INSERT INTO core_moviegenre (movie_id, genre_id) VALUES ({}, {})'.format(movie_id, genre_id)
    cursor.execute(query)


def insert_userprofile(username, email, password, is_superuser = False):
    url = 'http://127.0.0.1:8000/register/'
    data = {
        "username": username,
        "email": email,
        "password": password,
        "is_superuser": is_superuser
    }
    answer = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    if answer.status_code != 201:
        print('Bad request')
        print(answer.text)


def insert_movie(movie_id, title, release_date, summary, imdb_id, image_link, cursor):
    title = title.replace('\'', '\'\'')
    query = 'INSERT INTO core_movie (id, title, release_date, summary, imdb_id, image_link) VALUES' \
            '({}, \'{}\', \'{}\', \'{}\', \'{}\', \'{}\')'.format(movie_id, title, release_date, summary, imdb_id, image_link)
    cursor.execute(query)


def insert_hall(title, row_count, column_count, summary, cursor):
    query = 'INSERT INTO core_hall (title, row_count, column_count, summary) VALUES (\'{}\', {}, {}, \'{}\')' \
            ''.format(title, row_count, column_count, summary)
    cursor.execute(query)


def truncate(cursor):
    query = '''
    truncate table core_genre RESTART IDENTITY cascade;
    truncate table core_movie RESTART IDENTITY cascade;
    truncate table core_moviegenre RESTART IDENTITY cascade;
    truncate table core_ratings RESTART IDENTITY cascade;
    truncate table auth_user RESTART IDENTITY cascade;
    '''
    cursor.execute(query)


def get_random_string(length):
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))


def get_random_alphanumeric_string(length):
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join((random.choice(letters_and_digits) for i in range(length)))


def get_random_date():
    return '{}-{}-{}'.format(random.randrange(1990, 2021), random.randrange(1, 13), random.randrange(1, 29))


def main():
    database_name = 'cinema'
    username = 'postgres'
    password = 'password'
    host = 'localhost'

    conn = psycopg2.connect(dbname=database_name, user=username,
                            password=password, host=host)

    path_data = '/Users/dynamic-pie/smart_cinema/utils/data'
    movies = pd.read_csv(path_data + "/movies.csv")
    ratings = pd.read_csv(path_data + "/ratings.csv")
    links = pd.read_csv(path_data + "/links.csv", dtype={'imdbId':object})

    movies = movies.merge(links, left_on='movieId', right_on='movieId')

    movies['year'] = movies.title.str.extract("\((\d{4})\)", expand=True)
    movies.year = pd.to_datetime(movies.year, format='%Y')
    movies.year = movies.year.dt.year  # As there are some NaN years, resulting type will be float (decimals)
    movies.title = movies.title.str[:-7]

    static_path = 'http://127.0.0.1:8000/static/tt'
    email_domains = ['gmail.com', 'mail.ru', 'yandex.ru', 'yahoo.com', 'bmstu.ru', 'rambler.ru', 'microsoft.com']

    cursor = conn.cursor()
    truncate(cursor)
    conn.commit()

    cursor.execute('SELECT movie_id, poster_url FROM core_poster')
    records = cursor.fetchall()

    genre_map = {}
    index = 1
    genres_unique = pd.DataFrame(movies.genres.str.split('|').tolist()).stack().unique()
    for genre in genres_unique:
        insert_genre(genre, cursor)
        genre_map[genre] = index
        index += 1

    count = 0
    for movie in movies.itertuples(index=True, name='Pandas'):
        year = movie.year
        if math.isnan(year) is False:
            year = str(int(movie.year))+'-01-01'
        else:
            year = '1900-01-01'

        insert_movie(movie.movieId, movie.title, year, 'summary', movie.imdbId, records[count][1], cursor)
        movie_genre = movie.genres.split('|')
        for genre in movie_genre:
            insert_moviegenre(movie.movieId, genre_map[genre], cursor)

    print('Movie genre!')

    count_of_users = 5000
    for user in range(count_of_users):
        insert_userprofile(
            get_random_string(random.randrange(6, 20)),
            get_random_string(random.randrange(6, 20)) + '@' + random.choice(email_domains),
            get_random_alphanumeric_string(random.randrange(8, 20))
        )

    print('Users downloaded!')

    for rating in ratings.itertuples(index=True, name='Pandas'):
        if rating.userId <= count_of_users:
            insert_ratings(rating.rating, get_random_date(), rating.movieId, rating.userId, cursor)
        else:
            break
    insert_hall('Small hall', 10, 20, 'Hall for not big group', cursor)
    insert_hall('Medium hall', 20, 30, 'Hall include 3d', cursor)
    insert_hall('IMAX 3d hall', 45, 50, 'IMAX', cursor)
    conn.commit()
    cursor.close()
    conn.close()

    insert_userprofile('admin', 'art.dynamic.pie@gmail.com', 'password', True)


if __name__ == '__main__':
    main()
