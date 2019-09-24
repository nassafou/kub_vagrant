#!/bin/bash

MYSQL_PWD=yata mysql -h 172.17.0.3 -u yata <dump_yata_host1.sql
MYSQL_PWD=yata mysql -h 172.17.0.4 -u yata <dump_yata_host2.sql
MYSQL_PWD=yata mysql -h 172.17.0.5 -u yata <dump_yata_host3.sql

