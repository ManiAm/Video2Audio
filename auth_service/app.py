#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import bcrypt
from datetime import timedelta
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

from models import db, User

app = Flask(__name__)

# JWT
app.config['JWT_SECRET_KEY'] = 'my-super-secure-secret'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
jwt = JWTManager(app)

# PostgreSQL DB Interaction
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@db_auth:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

#######################################################

class UserManager:

    @staticmethod
    def hash_password(password):
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')

    @staticmethod
    def verify_password(password, hashed_password):
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


@app.route('/register', methods=['POST'])
def register():

    data = request.json

    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'message': 'Username, password and email are required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'User already exists'}), 409

    hashed_pw = UserManager.hash_password(password)

    new_user = User(username=username, password=hashed_pw, email=email)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Registered successfully'}), 201


@app.route('/login', methods=['POST'])
def login():

    data = request.json

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not UserManager.verify_password(password, user.password):
        return jsonify({'message': 'Login failed'}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "username": user.username,
            "email": user.email
        }
    )

    return jsonify(token=access_token)

#######################################################

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).first()
    return jsonify({'message': f'Welcome {user.username}!'})

#######################################################

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=5001)
