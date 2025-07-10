#!/bin/bash

# Connect to host MySQL instead of Docker container
mysql -h host.docker.internal -u redrat -p"$MYSQL_PASSWORD" redrat_proxy < mysql_schema.sql