import grpc
import generated.post_pb2 as post_service_pb2
import generated.post_pb2_grpc as post_service_pb2_grpc


class PostServiceClient():
    def __init__(self):
        self.channel = grpc.insecure_channel("post-service:50051")
        self.stub = post_service_pb2_grpc.PostServiceStub(self.channel)


    def CreatePost(self, author_id, content):
        result = self.stub.CreatePost(post_service_pb2.CreatePostRequest(
            AuthorId=author_id,
            Content=content))
        return result.PostId


    def GetPost(self, post_id):
        result = self.stub.GetPost(post_service_pb2.GetPostRequest(PostId=post_id))
        if not result.Success:
            return None
        return {
            "id": result.Post.Id,
            "authorId": result.Post.AuthorId,
            "createdAt": result.Post.CreatedAt.ToJsonString(),
            "content": result.Post.Content
        }


    OK = 0
    POST_NOT_FOUND = 1
    POST_NOT_OWNED = 2
    def UpdatePost(self, post_id, author_id, content):
        result = self.stub.UpdatePost(post_service_pb2.UpdatePostRequest(
            PostId=post_id,
            AuthorId=author_id,
            Content=content
        ))
        if not result.Success:
            match result.Error:
                case post_service_pb2.Error.PostNotFound:
                    return self.POST_NOT_FOUND
                case post_service_pb2.Error.PostNotOwned:
                    return self.POST_NOT_OWNED
        return self.OK


    def DeletePost(self, post_id, author_id):
        result = self.stub.DeletePost(post_service_pb2.DeletePostRequest(
            PostId=post_id,
            AuthorId=author_id
        ))
        if not result.Success:
            match result.Error:
                case post_service_pb2.Error.PostNotFound:
                    return self.POST_NOT_FOUND
                case post_service_pb2.Error.PostNotOwned:
                    return self.POST_NOT_OWNED
        return self.OK


    def GetPosts(self, page, size):
        result = self.stub.GetPosts(post_service_pb2.GetPostsRequest(
            Page=page,
            Size=size
        ))
        return [{
            "id": post.Id,
            "authorId": post.AuthorId,
            "createdAt": post.CreatedAt.ToJsonString(),
            "content": post.Content
        } for post in result.Posts]
