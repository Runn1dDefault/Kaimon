FROM python:3.11.9-alpine3.19

RUN apt-get update

WORKDIR /app

RUN pip install --upgrade pip

COPY ./requirements.txt ./

RUN pip install -r requirements.txt

COPY . .
