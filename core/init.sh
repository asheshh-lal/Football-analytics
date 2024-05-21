set -e

python /manage.py makemigrations
python /manage.py migrate


# docker compose -f docker-compose.yml run app ./init.sh
#