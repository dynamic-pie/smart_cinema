sudo apt update
sudo apt install python3-django
sudo apt install python3-pip
sudo apt install python3-venv

cd ~/smart_cinema
python3 -m venv my_env
source my_env/bin/activate

pip install django
python manage.py makemigrations
python manage.py makemigrations core
python manage.py migrate

python manage.py runserver

python utils/load_database.py