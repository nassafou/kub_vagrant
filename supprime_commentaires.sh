#!/bin/sh

for fic in "$@"

do 
 # supprimer les lignes blanches
  sed -e '/^[[blank:]]*$/d' $fic | 
# les commentaires

  sed -e '/^[[blank:]]*#/d' $fic 

done 
