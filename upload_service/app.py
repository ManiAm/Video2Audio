#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import datetime
import json
import pika
import gridfs
from pymongo import MongoClient
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt

app = Flask(__name__)

# JWT - must match with auth_service
app.config["JWT_SECRET_KEY"] = "my-super-secure-secret"
jwt = JWTManager(app)

mongo_client = MongoClient("mongodb://db_mongo:27017")
db = mongo_client["media"]
fs = gridfs.GridFS(db)
db.fs.files.create_index("created_at", expireAfterSeconds=3600)  # Set TTL to 3600 seconds (1 hour)


@app.route("/upload", methods=["POST"])
@jwt_required()
def upload_video():

    file = request.files.get("file")

    if not file or file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    user_id = get_jwt_identity()
    claims = get_jwt()
    user_email = claims["email"]

    video_id = fs.put(
        file,
        filename=file.filename,
        content_type=file.content_type,
        metadata={
            "uploaded_by": user_id,
            "upload_time": datetime.datetime.utcnow()
        },
        created_at=datetime.datetime.utcnow()
    )

    send_rabbitmq_message(video_id, user_id, user_email)

    return jsonify({"message": "File uploaded", "video_id": str(video_id)}), 200


def send_rabbitmq_message(video_id, user_id, user_email):

    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    channel = connection.channel()

    channel.queue_declare(queue="video_queue", durable=True)

    message = json.dumps({
        "video_id": str(video_id),
        "user_id": user_id,
        "email": user_email
    })

    channel.basic_publish(
        exchange="",
        routing_key="video_queue",
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)  # making message persistent
    )

    connection.close()


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5003)
