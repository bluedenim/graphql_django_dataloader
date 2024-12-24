FROM python:3.11-bookworm
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt update && apt install -y \
    vim

COPY requirements.txt /code/

RUN pip install --upgrade pip && pip install -r requirements.txt
