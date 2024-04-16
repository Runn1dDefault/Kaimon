FROM python:3.11-slim

RUN apt-get update

WORKDIR /app

RUN pip install --upgrade pip

COPY ./requirements.txt ./

RUN pip install -r requirements.txt

COPY . .

RUN ["chmod", "+x", "web-runner.sh"]
