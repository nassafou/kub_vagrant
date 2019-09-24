#!/bin/bash

hosts=`cat /home/bob/kub_vagrant/testPHP/hosts | awk 'match($0,/192(.[0-9]+)+/){print substr($0,RSTART,RLENGTH)}'`
databases="yata1 yata2 yata3"

for host in $hosts;do
	echo ""
	echo "Drop sur ${host}..."
	for database in ${databases};do
  	for j in $(seq 1 10);do
			MYSQL_PWD=yata mysql -h ${host} -u yata -e "TRUNCATE table${j};" ${database}
		done
	done
done

