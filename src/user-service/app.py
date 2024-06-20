#!/flask/bin/python
from flask import Flask, request, jsonify
import redis
import bcrypt
import secrets
import json
from collections import defaultdict
import re
import requests

from post_service_client import PostServiceClient

from kafka import KafkaProducer

r = redis.Redis(host='user-service-db', port=6379, db=0)
app = Flask(__name__)

ps_client = PostServiceClient()

kafka_producer = KafkaProducer(bootstrap_servers='stat-kafka:9092', value_serializer=lambda v: json.dumps(v).encode())

def verify_login_or_password(str):
    for c in str:
        if not c.isalpha() and not c.isnumeric() and c != '-' and c != '_':
            return False
    return True


def calc_hash(password: str, auth_data):
    if auth_data["version"] == "bcrypt":
        return bcrypt.hashpw(password.encode(), auth_data["salt"].encode()).decode()
    raise ValueError("unrecognized hash version")


def generate_token(id):
    return str(id) + "$" + secrets.token_hex(16)


@app.post('/register')
def register():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415

    data = request.get_json()

    if not "login" in data or not "password" in data:
        return {"error": "Request must contain login and password"}, 400
    if not verify_login_or_password(data["login"]):
        return {"error": "Invalid login"}, 400
    if not verify_login_or_password(data["password"]):
        return {"error": "Invalid password"}, 400

    if not r.get("auth$" + data['login']) is None:
        return {"error": "Login already in use"}, 409

    auth_data = {}
    # we write the version, so we can change
    # it in the future, without invalidating old passwords
    auth_data["version"] = "bcrypt"
    auth_data["salt"] = bcrypt.gensalt().decode()
    auth_data["hash"] = calc_hash(data["password"], auth_data)
    # generate user id
    auth_data["id"] = int(r.incr("user_ids"))
    r.set("auth$" + data['login'], json.dumps(auth_data))
    # generate empty user data
    r.set("user_data$" + str(auth_data["id"]), json.dumps({"id":auth_data["id"]}))
    # generate a session token
    token = generate_token(auth_data["id"])
    r.set("token$" + str(auth_data["id"]), token)
    return jsonify({"token": token})


@app.post('/login')
def login():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415

    data = request.get_json()

    if not "login" in data or not "password" in data:
        return {"error": "Request must contain login and password"}, 400
    if not verify_login_or_password(data["login"]):
        return {"error": "Invalid login"}, 400
    if not verify_login_or_password(data["password"]):
        return {"error": "Invalid password"}, 400

    key = "auth$" + data['login']
    raw_data = r.get(key)
    if raw_data is None:
        return {"error": "Incorrect password or login doesn't exist"}, 401
    auth_data = json.loads(raw_data.decode())
    hash = calc_hash(data["password"], auth_data)
    if hash != auth_data["hash"]:
        return {"error": "Incorrect password or login doesn't exist"}, 401
    # find a session token
    return jsonify({"token": r.get("token$" + str(auth_data["id"])).decode()})


def validate_token(token):
    if not '$' in token:
        return None
    id = token.split("$")[0]
    if r.get("token$" + id).decode() == token:
        return int(id)
    return None


def _info_get(id):
    raw_data = r.get("user_data$" + str(id))
    if raw_data is None:
        return {"error": "User not found"}, 404
    data = defaultdict(str, json.loads(raw_data))
    return jsonify({
        "id": id,
        "firstName": data["firstName"],
        "lastName": data["lastName"],
        "birthDate": data["birthDate"],
        "email": data["email"],
        "phone": data["phone"]})


@app.get('/user/<id>/info')
def info_get(id):
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401
    return _info_get(id)


@app.get('/user/me/info')
def my_info_get():
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401
    return _info_get(my_id)


data_rules = {
    "firstName": r"^[a-zA-Z]{3,30}$",
    "lastName": r"^[a-zA-Z]{3,30}$",
    "email": r"^\S+@\S+\.\S+$",
    "phone": r"^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$",
    "birthDate": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
}


@app.put('/user/me/info')
def my_info_put():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    id = validate_token(token)
    if id is None:
        return {"error": "Unauthorized"}, 401
    old_data = json.loads(r.get("user_data$" + str(id)))
    data = request.get_json()
    for key, val in data.items():
        if key not in data_rules:
            return {"error": "Unknown field: " + key}, 400
        if not re.match(data_rules[key], val):
            return {"error": "Invalid value of field: " + key}, 400
        old_data[key] = val
    r.set("user_data$" + str(id), json.dumps(old_data))
    return "", 200


@app.post('/posts/create')
def create_post():
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    id = validate_token(token)
    if id is None:
        return {"error": "Unauthorized"}, 401
    data = request.get_json()

    if not "content" in data:
        return {"error": "Content not set"}, 400

    content = data["content"]

    post_id = ps_client.CreatePost(id, content)
    return {"post_id": post_id}


@app.get('/posts/<id>')
def get_post(id):
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401

    if not id.isdigit():
        return {"error": "Id must be integer"}, 400
    id = int(id)

    post = ps_client.GetPost(id)
    if post is None:
        return {"error": "Post not found"}, 404
    return post


@app.put('/posts/<id>')
def update_post(id):
    if not request.is_json:
        return {"error": "Request must be JSON"}, 415
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401
    data = request.get_json()

    if not "content" in data:
        return {"error": "Content not set"}, 400

    if not id.isdigit():
        return {"error": "Id must be integer"}, 400
    id = int(id)

    status = ps_client.UpdatePost(id, my_id, data["content"])
    if status == PostServiceClient.OK:
        return ""
    if status == PostServiceClient.POST_NOT_FOUND:
        return {"error": "Post not found"}, 404
    if status == PostServiceClient.POST_NOT_OWNED:
        return {"error": "Post not owned"}, 403


@app.delete('/posts/<id>')
def delete_post(id):
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401

    if not id.isdigit():
        return {"error": "Id must be integer"}, 400
    id = int(id)

    status = ps_client.DeletePost(id, my_id)
    if status == PostServiceClient.OK:
        return ""
    if status == PostServiceClient.POST_NOT_FOUND:
        return {"error": "Post not found"}, 404
    if status == PostServiceClient.POST_NOT_OWNED:
        return {"error": "Post not owned"}, 403


@app.get('/posts/feed')
def get_feed():
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401

    page = 0
    page_from_args = request.args.get("page")
    if not page_from_args is None:
        if not page_from_args.isdigit() or int(page_from_args) < 0:
            return {"error": "page must be a non-negative integer"}, 400
        page = int(page_from_args)
    size = 50
    size_from_args = request.args.get("size")
    if not size_from_args is None or int(size_from_args) <= 0:
        if not size_from_args.isdigit():
            return {"error": "size must be a positive integer"}, 400
        size = int(size_from_args)

    result = ps_client.GetPosts(page, size)
    if len(result) == 0 and page > 0:
        # page > 0 because if there are no posts at all and user asks for first page we shouldn't throw error
        return {"error": "Page doesn't exist"}, 404
    return result


@app.put('/posts/<id>/like')
def like_post(id):
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401

    if not id.isdigit():
        return {"error": "Id must be integer"}, 400
    id = int(id)

    post = ps_client.GetPost(id)
    if post is None:
        return {"error": "Post not found"}, 404

    kafka_producer.send("events", {
        "user_id": my_id,
        "post_id": id,
        "author_id": post["authorId"],
        "type": "like"
    })

    return ""


@app.put('/posts/<id>/view')
def view_post(id):
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401

    if not id.isdigit():
        return {"error": "Id must be integer"}, 400
    id = int(id)

    post = ps_client.GetPost(id)
    if post is None:
        return {"error": "Post not found"}, 404

    kafka_producer.send("events", {
        "user_id": my_id,
        "post_id": id,
        "author_id": post["authorId"],
        "type": "view"
    })

    return ""


@app.get('/posts/<id>/stats')
def get_stats(id):
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401

    if not id.isdigit():
        return {"error": "Id must be integer"}, 400
    id = int(id)

    post = ps_client.GetPost(id)
    if post is None:
        return {"error": "Post not found"}, 404

    response = requests.get(f"http://stat-service:5000/posts/{id}/stats")
    return response.json()


@app.get('/posts/top')
def top_posts():
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    id = validate_token(token)
    if id is None:
        return {"error": "Unauthorized"}, 401

    response = requests.get(f"http://stat-service:5000/posts/top")
    return response.json()


@app.get('/users/top')
def tops_users():
    if request.authorization is None or request.authorization.token is None:
        return {"error": "Unauthorized"}, 401
    token = request.authorization.token
    id = validate_token(token)
    if id is None:
        return {"error": "Unauthorized"}, 401

    response = requests.get(f"http://stat-service:5000/users/top")
    return response.json()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
