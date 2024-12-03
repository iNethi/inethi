#!/bin/bash

FLAG="/firstboot.log"

if [[ ! -f $FLAG ]]; then
   echo "Initializing MariaDB for the first time..."

   # Wait for MariaDB to be ready
   while ! mysqladmin ping -h"localhost" --silent; do
       echo "Waiting for MariaDB to start..."
       sleep 2
   done

   echo "-- CONFIGURING TIME ZONES"
   mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root mysql

   echo "-- CONFIGURING PRIVILEGES"
   mysql -u root < /tmp/db_priveleges.sql

   echo "-- IMPORTING RADIUSDESK TABLES"
   mysql -u root rd < /tmp/rd.sql

   touch "$FLAG"
   echo "Completed database initialization."
else
   echo "MariaDB initialization already completed."
fi
