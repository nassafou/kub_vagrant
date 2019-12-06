#!/bin/sh


REP_TRACES=/var/log

cd $REP_TRACES

cat /dev/null > messages
cat /dev/null > wtmp
echo "Journaux nettoyés."

exit # la bonne methode pour sortir d'un script
