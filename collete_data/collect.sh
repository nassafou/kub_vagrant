#!/bin/bash

date_jour=`date +%Y-%m-%d`

# taille des bases

MYSQL_PWD=yata mysql -u yata -sN -e "SELECT table_schema 'Data Base Name', round(sum( data_length + index_length) / 1024 / 1024, 2) 'Data Base Size in MB' FROM information_schema.TABLES where table_schema not in ('mysql', 'performance_schema', 'information_schema') GROUP BY table_schema ;"| tr "\t" ";" | awk -v date_jour="$date_jour" -v host="$HOSTNAME" '{print date_jour";"host";"$0}'

# nombre de tables

MYSQL_PWD=yata mysql -u yata -sN -e "select table_schema, count(*) from information_schema.TABLES where table_schema not in ('mysql', 'performance_schema', 'information_schema')group by TABLE_SCHEMA;"| tr "\t" ";" |  awk -v date_jour="$date_jour" -v host="$HOSTNAME" '{print date_jour";"host";"$0}'

# nombre lignes par table

MYSQL_PWD=yata mysql -u yata -sN -e "select table_schema,table_name,TABLE_ROWS from information_schema.TABLES where table_schema not in ('mysql', 'performance_schema', 'information_schema') group by TABLE_SCHEMA,table_name;"| tr "\t" ";" |  awk -v date_jour="$date_jour" -v host="$HOSTNAME" '{print date_jour";"host";"$0}'



