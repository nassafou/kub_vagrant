#!/bin/bash

#passwdir=~/kub_vagrant
#checkdir() {
#   if [ -e $passwdir ]; then
#        echo "le fichier $passwdir existe"
#       else 
#        echo "Le fichier $passwdir n'existe pas "
#   fi
#}
#checkdir
#exit
#~/kub_vagrant

passwdir=~/kub_vagrant

if [ -d $passwdir ]; then
     echo "le fichier $passwdir existe"
    else
     echo " Le fichier $passwdir n'existe pas"
fi
