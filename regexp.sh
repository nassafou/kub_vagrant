#! /bin/sh

EXPRESSION="$1"

shift

for chaine in "$@"
do
  echo "$chaine" | grep "$EXPRESSION" > /dev/null
  if [ $? -eq 0 ]
  then 
      echo "$chaine : OUI"
  else
     echo "$chaine : NON"
  fi

done
