#!/bin/bash

# Connect to host MySQL instead of Docker container
# Use the MYSQL_DB environment variable to ensure consistency
mysql -h host.docker.internal -u ${MYSQL_USER:-redrat} -p"${MYSQL_PASSWORD:-redratpass}" ${MYSQL_DB:-redrat_proxy} < mysql_schema.sql