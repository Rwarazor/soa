#!/bin/bash
cd $(cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. post.proto

cp post_pb2_grpc.py post_pb2.py ../post-service/generated/
cp post_pb2_grpc.py post_pb2.py ../user-service/generated/
