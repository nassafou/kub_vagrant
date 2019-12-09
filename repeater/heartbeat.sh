#!/bin/bash

set -e
trap "echo SIGNAL" HUP INT QUIT KILL TERM

if [ -z "$HEARTBEATSTEP"]; then
 echo "la var d'en "
 return 1
fi

while true;
do 
  echo $1 \($(date +%H:%M:%S)\);
  sleep "$HEARTBEATSTEP";
done
