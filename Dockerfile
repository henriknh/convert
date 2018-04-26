FROM alpine:latest
RUN apk update

ADD convert.py convert.py

RUN apk add --no-cache \
    ffmpeg \
    python3 \
    python3-pip

RUN pip3 install \
    pyinotify

ENTRYPOINT ["python3", "convert.py"]
