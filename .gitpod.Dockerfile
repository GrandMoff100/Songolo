ARG PY_VERSION=3.8
FROM docker.io/python:${PY_VERSION}

RUN sudo apt-get install ffmpeg -yq
RUN pip install poetry
RUN poetry config virtualenvs.create false
