FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv

RUN apt-get update && \
    apt-get install -y \
        libpq-dev \
        gcc \
        python3 \
        python3-pip \
        python3-venv

RUN python3 -m venv $VIRTUAL_ENV

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install flask flask_jwt_extended flask_sqlalchemy psycopg2 bcrypt PyJWT

COPY app.py /app/app.py
COPY models.py /app/models.py

WORKDIR /app

EXPOSE 5000

CMD ["python", "app.py"]
