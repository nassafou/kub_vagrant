#!/bin/sh
echo "Liste des utilisateurs dans /etc/passwd"
for params in `cat /etc/passwd | cut -d: -f1`
do
    echo "$params "
done
