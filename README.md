
# Video2Audio

Video2Audio is an intuitive web application that enables users to authenticate, upload video files, and retrieve the extracted audio tracks. The platform is built on a microservices architecture with separated responsibilities, ensuring scalability, maintainability, and fault isolation. The system leverages:

- **PostgreSQL** for secure storage of user credentials
- **MongoDB** for efficient storage of media files (videos and audios)
- **RabbitMQ** as a message broker for asynchronous task processing

Each microservice runs in its own isolated container, all connected through a shared custom Docker bridge network. All service containers are based on lightweight Ubuntu 22.04 images, with necessary dependencies installed for each service's specific requirements.

## System Architecture

Here is the project structure:

```text
Video2Audio/
├── auth_service/         # Authentication microservice (register/login)
│   ├── app.py
│   ├── Dockerfile
│   └── models.py
├── upload_service/       # Microservice to upload videos to MongoDB and notify workers
│   ├── app.py
│   ├── Dockerfile
├── convertor_service/    # Video to audio conversion microservice
│   ├── app.py
│   ├── Dockerfile
├── frontend/             # Basic Frontend
│   ├── app.py
│   ├── Dockerfile
│   ├── templates/
│   │   ├── register.html
│   │   ├── login.html
│   │   ├── upload.html
├── docker-compose.yml
```

### Authentication Service

The `auth_service` is responsible for managing user authentication through the use of JSON Web Tokens (JWT).

#### User Registration

New users must first register by sending a `POST` request to the `/register` endpoint with their desired username and password. An example curl command for registration:

```bash
curl -X POST http://localhost:5001/register \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser", "password": "mypassword"}'
```

Upon successful registration, the server responds with:

```text
{"message":"Registered successfully"}
```

In the backend, the system securely stores user credentials in a PostgreSQL database. Passwords are never stored in plaintext. Instead, they are hashed using a cryptographically secure algorithm — `bcrypt`. Unlike basic hashing methods, bcrypt applies a salt (a random value) to each password before hashing, providing strong protection against rainbow table attacks. It is intentionally computationally expensive, making brute-force attacks significantly harder by slowing down each password guess attempt. This approach ensures that even if the database is compromised, user credentials remain strongly protected.

#### User Login

To log in, users send a `POST` request to the `/login` endpoint with their username and password:

```bash
curl -X POST http://localhost:5001/login \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser", "password": "mypassword"}'
```

During the login process, the backend retrieves the user record and hashed password from PostgreSQL. It then verifies the provided password against the stored bcrypt hash. Upon successful verification, it generates a JWT access token that remains valid for one hour.

```text
{"token":"<your_jwt_token>"}
```

Once a JWT token is obtained, users can access protected endpoints by including the token in the Authorization header. For example, to access the `/protected` route:

```bash
curl -X GET http://localhost:5001/protected \
  -H "Authorization: Bearer <your_jwt_token>"
```

If the token is valid and not expired, the request is authorized and the server responds accordingly.

### Upload Service

After successful authentication, the obtained JWT token can also be used to securely access other services within the system, including the upload service, by including it in the authorization headers of subsequent API requests.

Here is a POST request to send a MP4 video file to the upload service:

```bash
curl -X POST http://upload_service:5003/upload \
  -H "Authorization: Bearer <your_jwt_token>" \
  -F "file=@/path/to/your/video.mp4"
```

The `/upload` endpoint in the upload_service is protected by the `@jwt_required()` decorator, which enforces that only authenticated users can access this functionality. Clients must include a valid JWT token in the Authorization header of their POST request. If the token is missing or invalid, the upload request will be rejected with an appropriate error response.

JWT (JSON Web Token) is a self-contained, digitally signed token that carries all necessary user information internally (such as username, expiration time ,etc.). Since the upload_service is configured with the shared JWT_SECRET_KEY, it can validate the token locally without making additional network calls to the authentication service. This approach improves performance, reduces latency, and allows the system to scale more efficiently under high load.

Once the authenticated request is validated, the received video file is saved into MongoDB using GridFS, a specification built for handling large binary files efficiently. While relational databases (such as PostgreSQL or MySQL) provide a BLOB (Binary Large Object) type, they are generally not optimized for storing and serving large media files like videos or audios. MongoDB's GridFS breaks large files into chunks and stores them across multiple documents, making it a better choice for scalable media storage. This design ensures that media files of any size can be uploaded without hitting database size or performance limits typical of relational databases.

After successfully storing the uploaded media, the upload_service sends a message to a RabbitMQ message broker. RabbitMQ enables asynchronous communication between services. It decouples the upload process from further processing tasks, such as audio extraction. Specifically, a worker service (the converter_service) subscribes to the message queue and asynchronously picks up new upload tasks.

### Converter Service

To enable asynchronous communication between the upload_service and one or more instances of the converter_service, the system utilizes a RabbitMQ message broker. A queue named video_queue is created within the broker to serve as the communication channel. All messages published by the upload_service are sent to the default exchange, which is a special direct exchange with an empty string ("") as its name. In RabbitMQ, queues bound to the default exchange automatically use their queue name as the routing key, meaning the video_queue is implicitly bound with a routing key of "video_queue".

Multiple instances of the converter_service are subscribed to the same queue (video_queue), forming a classic competing consumers setup. This pattern improves throughput, scalability, and fault tolerance by allowing multiple workers to process messages concurrently. RabbitMQ distributes incoming messages to consumers in a round-robin fashion, ensuring load balancing. If one converter_service instance is busy or slow, RabbitMQ automatically forwards the next message to another available instance, keeping the system responsive under load.

To prevent data loss in the event of a broker crash, service failure, or network disruption, the following message durability mechanisms are implemented:

- Durable Queue: The video_queue is declared with the `durable=True` flag. This instructs RabbitMQ to persist the queue definition and metadata to disk, ensuring it survives broker restarts. The queue and its bindings are automatically restored when the broker comes back online.

- Persistent Messages: Messages sent by the upload_service are flagged as persistent by setting the `delivery_mode=2` property. This ensures that messages are written to disk by the broker instead of being held solely in memory. As a result, messages are not lost if the broker crashes before they are consumed.

To further improve message delivery guarantees, the system could implement the following:

- Manual Acknowledgements (basic_ack): Ensures messages are only removed from the queue after a consumer confirms successful processing.

- Publisher Confirms: Allows the producer (upload_service) to be notified when a message is successfully stored by the broker.

- Mandatory Flag: Ensures messages are returned to the producer if they cannot be routed to a queue, preventing silent message drops.

### Frontend

The frontend is the user-facing component of the system. It is built using Flask and provides a lightweight web interface that enables users to interact with the backend services. This service handles all user interactions including:

- Registration:

  New users can sign up by providing a username, password, and email address.

  These credentials are sent to the auth_service, where they are stored after password hashing.

- Login:

  Existing users authenticate with their credentials.

  Upon successful login, a JWT token is issued by the auth_service and stored in Flask session cookies.

  This enables secure, authenticated requests to the backend without repeatedly asking the user to log in.

- Video Upload:

  Authenticated users can upload video files through a simple web form.

  The uploaded file, along with the JWT token, is forwarded to the upload_service for processing.

Here is a summary of endpoints:

| Route            | Description                                               |
|------------------|-----------------------------------------------------------|
| `/register`      | User registration form (POSTs to `auth_service`)          |
| `/` or `/login`  | User login form (retrieves JWT token on success)          |
| `/upload`        | Upload interface for sending video files to the backend   |
| `/upload_success`| Displays a success message once the video is uploaded     |

## Getting Started

Clone the repository and change to the root folder:

```bash
cd Video2Audio
```

Build Docker image for all services:

```bash
docker compose build
```

Start all containers:

```bash
docker compose up -d
```

Once the containers are up, open your browser and navigate to:

```bash
http://localhost:5002
```

You will be able to:

- Register a new account
- Log in using your credentials
- Upload a video file
- Extract and store audio from the video
- Receive an email notification with download link to the audio file

<img src="pics/demo.gif" alt="segment">

Docker logs from the converter_service shows successful audio extraction:

```bash
docker logs convertor_service1

MoviePy - Writing audio in /tmp/temp_audio.mp3
MoviePy - Done.
Saving audio track to MongoDB
Audio created: 68116259f0d87e4f062f9407. Sending email to nima@gmail.com...
```

Uploaded videos and extracted audio files in MongoDB are automatically deleted after 1 hour.

## User Interaction Flow




## Telemetry


send MQTT status using telegraf to DB and visualize it

monitor msg queue status using telegraf

