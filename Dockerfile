FROM python:3.11-slim
EXPOSE 8000
RUN apt update && apt install -y curl
HEALTHCHECK --interval=1m --timeout=3s CMD curl --fail http://127.0.0.1:8000/ || exit 1
VOLUME /data
ENV PYTHONUNBUFFERED 1

COPY . /app
WORKDIR /app
RUN /usr/local/bin/pip install -r requirements.txt
RUN ln -s /data /app/data
CMD ["/usr/local/bin/flask", "run", "-h", "0.0.0.0", "-p", "8000"]
