ARG PY_VERSION=3.8
FROM docker.io/python:${PY_VERSION}

RUN pip install poetry
RUN poetry config virtualenvs.create false
