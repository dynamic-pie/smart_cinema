import psycopg2
import requests
import pandas as pd

def get_poster_url(imdb_id):
    url = 'http://www.omdbapi.com/?apikey=58c15082&i=tt' + imdb_id
    try:
        answer = requests.get(url)
        return answer.json()['Poster']
    except:
        return 'http://www.no.com'

def insert_poster(movie_id, imdb_id, poster_url, cursor):
    query = 'INSERT INTO core_poster (movie_id, imdb_id, poster_url) VALUES ({}, \'{}\', \'{}\')'.format(movie_id, imdb_id, poster_url)
    cursor.execute(query)

def truncate(cursor):
    query = '''
    truncate table core_poster RESTART IDENTITY cascade;
    '''
    cursor.execute(query)

def main():
    database_name = 'cinema'
    username = 'postgres'
    password = 'password'
    host = 'localhost'

    path_data = '/Users/dynamic-pie/smart_cinema/utils/data'

    conn = psycopg2.connect(dbname=database_name, user=username,
                            password=password, host=host)

    cursor = conn.cursor()
    truncate(cursor)
    conn.commit()

    links = pd.read_csv(path_data + "/links.csv", dtype={'imdbId':object})
    count = 0
    for link in links.itertuples(index=True, name='Pandas'):
        insert_poster(link.movieId, link.imdbId, get_poster_url(link.imdbId), cursor)
        count += 1
        print(count)

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()