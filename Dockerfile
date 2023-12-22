FROM python:3.11
LABEL authors="poti"
LABEL maintainer="andraz.podpecan1@student.um.si"


WORKDIR /mqtt-kafka-bridge
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["python3", "src/mqtt-python-bridge.py"]