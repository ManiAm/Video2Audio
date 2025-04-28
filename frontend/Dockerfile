FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv

RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv

RUN python3 -m venv $VIRTUAL_ENV

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install flask requests

COPY app.py /app/app.py
COPY templates/ /app/templates/

WORKDIR /app

EXPOSE 5002

CMD ["python", "app.py"]
