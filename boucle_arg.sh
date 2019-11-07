#! /bin/sh

i=0
while [ $i -lt 5 ] ; do
    echo $1
    i=$(( i + 1 ))
    sleep 1
done
