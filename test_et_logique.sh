echo -n "Fichier à examiner : " &&
read F &&
echo -n "Texte recherché: " &&
read T &&
grep $T $F > /dev/null &&
echo "le texte $T a été trouvé"
