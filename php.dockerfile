FROM php:fpm
RUN docker-php-ext-install mysqli
CMD ["php-fpm"]
