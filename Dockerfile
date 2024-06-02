FROM python:3.11-slim
EXPOSE 8000
RUN apt update && apt install -y rsync && rm -rf /var/lib/apt/lists/*
VOLUME /data
ENV PYTHONUNBUFFERED 1

COPY . /app
WORKDIR /app
RUN ln -s /data /app/data
RUN /usr/local/bin/pip install .
CMD ["/usr/local/bin/flask", "--app", "rav2", "run", "-h", "0.0.0.0", "-p", "8000"]
