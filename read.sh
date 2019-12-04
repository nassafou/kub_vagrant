#!/bin/sh

echo "Continuer (O/N) ? \c"

read reponse 
echo "reponse=$reponse"
case $reponse in 
      O) 
          echo "OUI, on continue"
          ;;
      
      N) 
          echo "OUI, on continue"
          ;;

      
      *) 
          echo "Erreur de saisie (O/N)"
          exit 1
          ;;
esac
echo "Vous avez continue. Tapez deux mots ou plus :\c"
