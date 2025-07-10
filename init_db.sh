#!/bin/bash
docker exec -i redrat-db mysql -uredrat -psecurepassword redrat_proxy < mysql_schema.sql