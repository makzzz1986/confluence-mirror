FROM python:3.13-slim

COPY requirements.pip .
COPY src/ /app/

RUN pip install -r requirements.pip

WORKDIR /app

CMD [ "python3", "main.py"]
