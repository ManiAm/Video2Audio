#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import json
import pika
import gridfs
from pymongo import MongoClient
from bson.objectid import ObjectId
from moviepy import VideoFileClip

mongo_client = MongoClient("mongodb://db_mongo:27017/")
db = mongo_client["media"]
fs = gridfs.GridFS(db)

connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()
channel.queue_declare(queue='video_queue', durable=True)

def callback(ch, method, properties, body):

    try:

        message = json.loads(body.decode())

        video_id = message["video_id"]
        user_id = message["user_id"]
        email = message["email"]

        # Retrieve video file from MongoDB
        video_file = fs.get(ObjectId(video_id))

        # Save the video temporarily
        with open("/tmp/temp_video.mp4", "wb") as f:
            f.write(video_file.read())

        # Extract audio
        audio_path = "/tmp/temp_audio.mp3"
        video = VideoFileClip("/tmp/temp_video.mp4")
        video.audio.write_audiofile(audio_path)

        print("Saving audio track to MongoDB", flush=True)

        with open(audio_path, "rb") as f:
            metadata={"original_video_id": video_id, "uploaded_by": user_id}
            audio_id = fs.put(f, filename=f"{video_id}.mp3", metadata=metadata)

        print(f"Audio created: {audio_id}. Sending email to {email}...", flush=True)

    except Exception as e:
        print(f"[ERROR] Exception during processing: {e}", flush=True)


channel.basic_consume(queue='video_queue', on_message_callback=callback, auto_ack=True)

print('Waiting for video messages...')
channel.start_consuming()
