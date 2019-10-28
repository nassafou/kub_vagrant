#! /bin/sh

 while true ; do 
     echo -n "[Commande]>"
     if ! read chaine ; then
       echo "Saisie invalide"
       break
     fi
     if [ -z "$chaine" ] ; then
        echo "Saisie vide"
        break
     fi
     if [ 
