# **Examples**

`\register:`
```
curl -X 'POST' \
  'http://127.0.0.1:5000/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "login": "rwarazor",
  "password": "qwerty123"
}'
```

`\login:`
```
curl -X 'POST' \
  'http://127.0.0.1:5000/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "login": "rwarazor",
  "password": "qwerty123"
}'
```

`GET \user\me\info:`
```
curl -X 'GET' \
  'http://127.0.0.1:5000/user/me/info' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer 1$3c23f77b3866403cd7726f83d8fa857a'
```

`PUT \user\me\info:`
```
curl -X 'PUT' \
  'http://127.0.0.1:5000/user/me/info' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer 1$3c23f77b3866403cd7726f83d8fa857a' \
  -H 'Content-Type: application/json' \
  -d '{
  "firstName": "John",
  "birthDate": "2024-06-15",
  "email": "john@email.com",
}'
```

`\user\{id}\info`

```
curl -X 'GET' \
  'http://127.0.0.1:5000/user/3/info' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer 1$3c23f77b3866403cd7726f83d8fa857a'
```

`\posts\create`

```
curl -X 'POST' \
  'http://127.0.0.1:5000/posts/create' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer 1$c2856873f1e1668c3b13f47d0c5b404d' \
  -H 'Content-Type: application/json' \
  -d '{
  "content": "This is a new post!"
}'
```

`GET \posts\{id}`

```
curl -X 'GET' \
  'http://127.0.0.1:5000/posts/2' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer 1$c2856873f1e1668c3b13f47d0c5b404d'
```

`PUT \posts\{id}`

```
curl -X 'PUT' \
  'http://127.0.0.1:5000/posts/1' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer 1$c2856873f1e1668c3b13f47d0c5b404d' \
  -H 'Content-Type: application/json' \
  -d '{
  "content": "This is an updated post!"
}'
```

`DELETE \posts\{id}`

```
curl -X 'DELETE' \
  'http://127.0.0.1:5000/posts/2' \
  -H 'accept: */*' \
  -H 'Authorization: Bearer 1$c2856873f1e1668c3b13f47d0c5b404d'
```

`\posts\feed`

```
curl -X 'GET' \
  'http://127.0.0.1:5000/posts/feed?page=0&size=50' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer 1$c2856873f1e1668c3b13f47d0c5b404d'
```
