FROM python:3.10-alpine

WORKDIR /post-service

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

ENV PYTHONPATH "${PYTHONPATH}:./generated"

CMD ["python", "./server.py"]
