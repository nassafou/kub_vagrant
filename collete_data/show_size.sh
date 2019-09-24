#!/bin/bash
#hosts=`cat /home/bob/kub_vagrant/testPHP/hosts | awk'match($0,/1/){}'`
hosts="192.168.236.130 192.168.236.152 192.168.236.153"
for host in $hosts;do
MYSQL_PWD=yata mysql -h ${host} -u yata -sN -e "SELECT table_schema 'Data Base Name', round(sum( data_length + index_length) / 1024 / 1024, 2) 'Data Base Size in MB' FROM information_schema.TABLES where table_schema not in ('mysql', 'performance_schema', 'information_schema') GROUP BY table_schema ;"
done

