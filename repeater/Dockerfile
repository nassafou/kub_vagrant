FROM ubuntu:latest
ARG HEARTBEATSTEPDEFAULT=2
LABEL maintainer="yoz@gmail.com"
LABEL version="1.0"
LABEL description="This image emits a regular message on STDIN"
LABEL readme="the beatheart environement variable"
COPY heartbeat.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENV HEARTBEATSTEP ${HEARTBEATSTEPDEFAULT}
ENTRYPOINT ["/entrypoint.sh"]
CMD ["heartbeat"]

