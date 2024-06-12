#!/flask/bin/python
from flask import Flask, request, jsonify
import redis
import bcrypt
import secrets
import json
from collections import defaultdict
import re


r = redis.Redis(host='user-service-db', port=6379, db=0)
app = Flask(__name__)


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
    token = request.authorization.token
    if token is None:
        return {"error": "Unauthorized"}, 401
    my_id = validate_token(token)
    if my_id is None:
        return {"error": "Unauthorized"}, 401
    return _info_get(id)


@app.get('/user/me/info')
def my_info_get():
    token = request.authorization.token
    if token is None:
        return {"error": "Unauthorized"}, 401
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

    data = request.get_json()

    token = request.authorization.token
    if token is None:
        return {"error": "Unauthorized"}, 401
    id = validate_token(token)
    if id is None:
        return {"error": "Unauthorized"}, 401
    old_data = json.loads(r.get("user_data$" + str(id)))
    for key, val in data.items():
        if key not in data_rules:
            return {"error": "Unknown field: " + key}, 400
        if not re.match(data_rules[key], val):
            return {"error": "Invalid value of field: " + key}, 400
        old_data[key] = val
    r.set("user_data$" + str(id), json.dumps(old_data))
    return "", 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
