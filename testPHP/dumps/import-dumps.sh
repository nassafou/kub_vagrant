#!/bin/bash

MYSQL_PWD=yata mysql -h 192.168.236.130 -u yata <dump_yata_host1.sql
MYSQL_PWD=yata mysql -h 192.168.236.152 -u yata <dump_yata_host2.sql
MYSQL_PWD=yata mysql -h 192.168.236.153 -u yata <dump_yata_host3.sql

