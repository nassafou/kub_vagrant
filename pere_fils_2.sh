#! /bin/sh

funtion compte
{

 local i;
  for i in $(seq 3) ; do
      echo "$1 : $i"
      sleep 1
  done
}
