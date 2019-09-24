#!/bin/sh

hosts=`cat /home/bob/kub_vagrant/testPHP/hosts  | awk 'match($0,/192(.[0-9]+)+/) {print substr($0,RSTART,RLENGTH)}'`
echo $hosts
for host in $hosts;do
echo "Pour ${host}"
MYSQL_PWD=yata mysql -h $host -u yata -e "show databases;"
echo ""
done 
