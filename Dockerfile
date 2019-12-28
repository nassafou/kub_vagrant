FROM openclassroms/build_image

RUN apt-get update \
&&  apt-get upgrade -y \
&&  apt-get install nginx -y 


