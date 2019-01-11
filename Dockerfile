FROM alpine:latest
LABEL maintainer "Raman Shyshniou <rommer@ibuffed.com>"

EXPOSE 8080
RUN apk --no-cache add tini python3 py3-yaml py3-flask py3-requests uwsgi-python3

COPY . /app
WORKDIR /app

ENTRYPOINT [ "/sbin/tini", "--", "uwsgi",\
 "--master",\
 "--http-socket", "0.0.0.0:8080",\
 "--uid", "uwsgi",\
 "--plugins", "python3",\
 "--processes", "4",\
 "--locks", "1",\
 "--sharedarea", "4",\
 "--wsgi", "app:app" ]
