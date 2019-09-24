#!/bin/bash

## à faire tourner en root !!

date_jour=`date +%Y-%m-%d-%H-%M`

echo "### data for cmdb ####" >/var/log/datas.csv

############################# Base de données ######################################


# taille des bases

MYSQL_PWD=yata mysql -u yata -sN -e "SELECT table_schema 'Data Base Name', round(sum( data_length + index_length) / 1024 / 1024, 2) 'Data Base Size in MB' FROM information_schema.TABLES where table_schema not in ('mysql', 'performance_schema', 'information_schema') GROUP BY table_schema ;"| tr "\t" ";" | awk -v date_jour="$date_jour" -v host="$HOSTNAME" '{print date_jour";"host";db_taille;"$0}' >>/var/log/datas.csv

# nombre de tables

MYSQL_PWD=yata mysql -u yata -sN -e "select table_schema, count(*) from information_schema.TABLES where table_schema not in ('mysql', 'performance_schema', 'information_schema')group by TABLE_SCHEMA;"| tr "\t" ";" |  awk -v date_jour="$date_jour" -v host="$HOSTNAME" '{print date_jour";"host";db_tables;"$0}'>>/var/log/datas.csv

# nombre lignes par table

MYSQL_PWD=yata mysql -u yata -sN -e "select table_schema,table_name,TABLE_ROWS from information_schema.TABLES where table_schema not in ('mysql', 'performance_schema', 'information_schema') group by TABLE_SCHEMA, TABLE_NAME;"| tr "\t" ";" |  awk -v date_jour="$date_jour" -v host="$HOSTNAME" '{print date_jour";"host";db_lines;"$0}'>>/var/log/datas.csv


# Volume physique des bases


for database in $(MYSQL_PWD=yata mysql -u yata -sN -e "select table_schema from information_schema.TABLES where table_schema not in ('mysql', 'performance_schema', 'information_schema') group by TABLE_SCHEMA;");do
      sudo du -xksh /var/lib/mysql/* | grep ${database} | awk -v date_jour="$date_jour" -v host="$HOSTNAME" -v database="$database" '{print date_jour";"host";db_vol_physique;"database";"$1";"$2}'>>/var/log/datas.csv
done

############################# Système ################################################



# volume de la machine en Mo

volume=$(df -Plm | grep -v 'Filesystem' | awk '{sum += $2} END {print sum/1000}' 2> /dev/null)

# system OS

system=$(lsb_release -ds 2>/dev/null)

# mémoire

memoire=$(cat /proc/meminfo | grep MemTotal | awk '{printf("%.1f", $2/1024/1024);}')

echo "${volume};${system};${memoire}" | awk -v date_jour="$date_jour" -v host="$HOSTNAME" '{print date_jour";"host";system;"$0}'>>/var/log/datas.csv

############################# envoi ######################################


curl -i -X PUT 127.0.0.1:5000/datas?machine=$(hostname)\&type=mysql --upload-file /var/log/datas.csv

