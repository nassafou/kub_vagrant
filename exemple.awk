#! /usr/bin/awk -f

BEGIN { print "**** début****" }
END { print "**** fin****" }

{ print "*" $0 }

