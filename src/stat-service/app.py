#!/flask/bin/python
from flask import Flask, request, jsonify
import json

import clickhouse_connect
import threading

ch_client = clickhouse_connect.get_client(host="stat-service-db", port=8123)

app = Flask(__name__)

import sys

from kafka import KafkaConsumer

@app.get('/posts/<id>/stats')
def stats_get(id):
    likes = ch_client.query(f"SELECT count() as count FROM likes WHERE post_id = {id}")
    views = ch_client.query(f"SELECT count() as count FROM views WHERE post_id = {id}")
    return {"likes": likes.result_rows[0], "views": views.result_rows[0]}


@app.get('/posts/top')
def top_posts():
    top = ch_client.query('SELECT post_id, author_id, count() as likes_count FROM likes GROUP BY post_id ORDER BY likes_count DESC LIMIT 5')
    return [{"post_id": result[0], "author_id": result[1], "likes_count": result[2]} for result in top.result_rows]


@app.get('/users/top')
def top_users():
    top = ch_client.query('SELECT author_id, count() as likes_count FROM likes GROUP BY author_id ORDER BY likes_count DESC LIMIT 3')
    print(top.result_rows, file=sys.stderr)
    return [{"user_id": result[0], "likes_count": result[1]} for result in top.result_rows]

def consume_kafka():
    consumer = KafkaConsumer(
        "events",
        bootstrap_servers="stat-kafka:9092",
        value_deserializer=lambda x: json.loads(x.decode()))
    for message in consumer:
        print("here", message.value, file=sys.stderr)
        print(ch_client.query(f"SELECT * FROM views"))
        match message.value["type"]:
            case "view":
                ch_client.insert(
                    "views",
                    [[int(message.value["user_id"]), int(message.value["post_id"]), int(message.value["author_id"])]],
                    ["user_id", "post_id", "author_id"])
            case "like":
                ch_client.insert(
                    "likes",
                    [[int(message.value["user_id"]), int(message.value["post_id"]), int(message.value["author_id"])]],
                    ["user_id", "post_id", "author_id"])

if __name__ == '__main__':
    kafka_thread = threading.Thread(target=consume_kafka)
    kafka_thread.start()
    app.run(debug=True, host='0.0.0.0')
    kafka_thread.join()
