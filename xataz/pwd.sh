#! /bin/sh

  function pwd ()
  {
     A=${PWD%%$HOME*}
     echo ${A:-\~${PWD#$HOME}}
  }
