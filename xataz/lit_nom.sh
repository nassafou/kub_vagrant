#! /bin/sh

A=$(grep $USER /etc/passwd)
IFS=":"
read ident passe uid gid nom restant <<FIN
$A
FIN
echo "Le nom de $ident est : $nom"
