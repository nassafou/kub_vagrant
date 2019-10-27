#! /bin/sh

 function renvoie_un ()
 {
   return 1
 }

 function renvoie_zero ()
 {
   return 0 
 }

 echo -n "renvoie_un"
 if renvoie_un ; then echo vrai ; else echo faux ; fi
 echo -n "renvoie_zero: "
 if renvoie_zero ; then echo vrai ; else echo faux ; fi
