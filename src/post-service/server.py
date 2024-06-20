import generated.post_pb2_grpc as post_pb2_grpc
import generated.post_pb2 as post_pb2

from concurrent import futures
import grpc
import logging
import psycopg2
import sys

from google.protobuf.timestamp_pb2 import Timestamp

class PostServicer(post_pb2_grpc.PostServiceServicer):
    def __init__(self):
        self.connection = psycopg2.connect(
            "host=post-service-db "
            "port=5432 "
            "dbname=postgres "
            "user=postgres "
            "password=228322 "
            "target_session_attrs=read-write "
        )
        self.cursor = self.connection.cursor()
        logging.info("Ensuring existence of posts table")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS posts(id SERIAL, authorId integer, createdAt timestamp, content text);")
        self.connection.commit()


    def CreatePost(self, request, context):
        query = f"INSERT INTO posts (authorId, createdAt, content) VALUES ('{request.AuthorId}', now()::timestamp, %s) RETURNING id;"
        self.cursor.execute(query, (request.Content,))

        id = self.cursor.fetchone()[0]
        self.connection.commit()
        logging.debug(f'Created post with id = {id}')

        return post_pb2.CreatePostResponse(Success=True, PostId=id)


    def GetPost(self, request, context):
        query = f"SELECT id, authorId, createdAt, content FROM posts WHERE id = {request.PostId};"
        self.cursor.execute(query)

        res = self.cursor.fetchone()
        self.connection.commit()
        if res is None:
            return post_pb2.GetPostResponse(Success=False)
        id, authorId, createdAt, content = res
        logging.debug(f'Found post with id = {id}')

        ts = Timestamp()
        ts.FromDatetime(createdAt)

        return post_pb2.GetPostResponse(Success=True, Post=post_pb2.Post(
            Id=id,
            AuthorId=authorId,
            CreatedAt=ts,
            Content=content))


    def UpdatePost(self, request, context):
        query = f"SELECT authorId FROM posts WHERE id = {request.PostId};"
        self.cursor.execute(query)
        res = self.cursor.fetchone()

        if res is None:
            self.connection.commit()
            return post_pb2.UpdatePostResponse(Success=False, Error=post_pb2.Error.PostNotFound)

        authorId = res[0]

        if authorId != request.AuthorId:
            self.connection.commit()
            return post_pb2.UpdatePostResponse(Success=False, Error=post_pb2.Error.PostNotOwned)

        logging.debug(f'Updating post with id = {request.PostId}')
        query = f"UPDATE posts SET content = %s WHERE id = {request.PostId};"
        self.cursor.execute(query, (request.Content,))
        self.connection.commit()

        return post_pb2.UpdatePostResponse(Success=True)


    def DeletePost(self, request, context):
        query = f"SELECT authorId FROM posts WHERE id = {request.PostId};"
        self.cursor.execute(query)
        res = self.cursor.fetchone()

        if res is None:
            self.connection.commit()
            return post_pb2.UpdatePostResponse(Success=False, Error=post_pb2.Error.PostNotFound)

        authorId = res[0]

        if authorId != request.AuthorId:
            self.connection.commit()
            return post_pb2.UpdatePostResponse(Success=False, Error=post_pb2.Error.PostNotOwned)

        logging.debug(f'Deleting post with id = {request.PostId}')
        query = f"DELETE FROM posts WHERE id = {request.PostId};"
        self.cursor.execute(query)
        self.connection.commit()

        return post_pb2.UpdatePostResponse(Success=True)


    def GetPosts(self, request, context):
        query = f"SELECT id, authorId, createdAt, content FROM posts ORDER BY id DESC LIMIT {request.Size} OFFSET {request.Size * request.Page};"
        self.cursor.execute(query)
        res = self.cursor.fetchall()
        self.connection.commit()

        posts = []
        for id, authorId, createdAt, content in res:
            ts = Timestamp()
            ts.FromDatetime(createdAt)

            posts.append(post_pb2.Post(
                Id=id,
                AuthorId=authorId,
                CreatedAt=ts,
                Content=content))

        return post_pb2.GetPostsResponse(Posts=posts)


def serve():
    logging.info("Server starting")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    post_pb2_grpc.add_PostServiceServicer_to_server(PostServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    logging.info("Server started")
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    serve()
