#!/bin/bash

# le curler
docker run -tid --name curly alpine
docker exec -ti curly sh -c "apk add curl"

# le server web
docker run -tid --name netwb nginx
