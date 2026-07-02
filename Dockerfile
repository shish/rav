FROM python:3.14-slim
EXPOSE 8000
VOLUME /data
ENV PYTHONUNBUFFERED=1 UV_NO_DEV=1
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

COPY . /app
WORKDIR /app
RUN uv sync --locked
RUN ln -s /data /app/data
CMD ["uv", "run", "gunicorn", "-w", "4", "rav2:create_app()", "-b", "0.0.0.0:8000", "--access-logfile", "-"]
