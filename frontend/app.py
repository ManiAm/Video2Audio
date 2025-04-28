#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import requests
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)

# Flask session cookies
app.config['SECRET_KEY'] = "my-super-secure-session-key"


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    username = request.form["username"]
    password = request.form["password"]

    try:

        resp = requests.post("http://auth_service:5001/login", json={
            "username": username,
            "password": password
        })

        if resp.status_code == 200:
            session["token"] = resp.json()["token"]
            return redirect(url_for("upload"))

        return "Login failed", 401

    except Exception as e:
        return f"Error: {e}", 500


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    username = request.form["username"]
    password = request.form["password"]
    email = request.form["email"]

    try:

        resp = requests.post("http://auth_service:5001/register", json={
            "username": username,
            "password": password,
            "email": email
        })

        if resp.status_code == 201:
            return redirect(url_for("login"))  # Registration successful, go to login page

        return f"Registration failed: {resp.text}", resp.status_code

    except Exception as e:
        return f"Error: {e}", 500


@app.route("/upload", methods=["GET", "POST"])
def upload():

    if "token" not in session:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("upload.html")

    file = request.files.get("file")
    if not file or file.filename == "":
        return "No file uploaded", 400

    try:

        headers = {
            "Authorization": f"Bearer {session['token']}"
        }

        files = {
            "file": (file.filename, file.stream, file.content_type)
        }

        resp = requests.post("http://upload_service:5003/upload", headers=headers, files=files)

        # redirect after successful upload to prevent form resubmission when the user refreshes the page
        if resp.status_code == 200:
            session['upload_message'] = resp.text
            return redirect(url_for('upload_success'))

        return f"Upload failed: {resp.text}", resp.status_code

    except Exception as e:
        return f"Error during upload: {e}", 500


@app.route('/upload_success')
def upload_success():

    message = session.pop('upload_message', '')
    return f"<h1>Upload Successful!</h1><p>{message}</p>"


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5002)
