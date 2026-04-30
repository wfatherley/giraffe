#!/bin/bash

# activate development environment
echo "activating test environment:"
echo "============================"
echo ""
source .venv3132/bin/activate


# blackify
echo "running black @ 79 characters per line:"
echo "======================================="
echo ""
black -l 79 src/giraffe
echo ""


# lint
echo "running pylint:"
echo "==============="
echo ""
pylint src/giraffe
echo ""


# sqlite tests
echo "unit tests against sqlite:"
echo "=========================="
echo ""
export DB_DRIVER=sqlite
export DB_USER=
export DB_PASSWORD=
export DB_HOST=
export DB_PORT=
export DB_NAME=
echo "docker processes:"
echo "================="
echo "NONE"
echo ""
pytest -s
echo ""


# postgresql tests
echo "unit tests against postgresql:"
echo "=============================="
echo ""
export DB_DRIVER=postgresql
export DB_USER=postgres
export DB_PASSWORD=`python -m random -i 99999999`
export DB_HOST=0.0.0.0
export DB_PORT=5432
export DB_NAME=postgres
sleep 1
container=`docker run \
    --name giraffe-postgres \
    -e POSTGRES_PASSWORD=${DB_PASSWORD} \
    -p ${DB_PORT}:${DB_PORT} \
    -d postgres:latest`
echo "docker processes:"
docker ps
echo ""
echo "run unit tests (after sleeping for 7 seconds):"
sleep 7
pytest -s
docker stop $container > /dev/null
docker rm -v $container > /dev/null
echo ""


# mariadb tests
# echo "unit tests against mariadb:"
# echo "==========================="
# echo ""
# export DB_DRIVER=mariadb+mariadbconnector
# export DB_USER=giraffe
# export DB_PORT=3306
# export DB_NAME=giraffe
# sleep 1
# container=`docker run \
#     --name giraffe-mariadb \
#     -e MARIADB_ROOT_PASSWORD=${DB_PASSWORD} \
#     -e MARIADB_USER=${DB_USER} \
#     -e MARIADB_PASSWORD=${DB_PASSWORD} \
#     -e MARIADB_DATABASE=${DB_NAME} \
#     -p ${DB_PORT}:${DB_PORT} \
#     -d mariadb:latest`
# echo "docker processes:"
# docker ps
# echo ""
# echo "run unit tests (after sleeping for 7 seconds):"
# sleep 7
# docker logs $container
# #pytest -s
# docker stop $container > /dev/null
# docker rm -v $container > /dev/null
# echo ""
