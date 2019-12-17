#!/bin/sh

for i in  tmp $(pwd)
do
   echo " --- $i ---"
   ls $i
done

