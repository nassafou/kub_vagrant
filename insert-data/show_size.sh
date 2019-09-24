#!/bin/bash


hosts=`cat /home/bob/kub_vagrant/testPHP/hosts | awk 'match($0,/192(.[0-9]+)+/){print substr($0,RSTART,RLENGTH)}'`
echo ""

for host in $hosts;do
	echo ""
	echo "Sur ${host} "
	MYSQL_PWD=yata mysql -h ${host} -u yata -e "SELECT table_schema 'Data Base Name', sum( data_length + index_length) / 1024 / 1024 'Data Base Size in MB' FROM information_schema.TABLES GROUP BY table_schema ;"
done

echo ""

