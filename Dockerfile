FROM astral/uv:0.13.6-alpine
EXPOSE 8000
VOLUME /data
COPY . /app
WORKDIR /app
RUN uv sync --locked --no-dev
RUN ln -s /data /app/data
CMD ["uv", "run", "--no-sync", "gunicorn", "-w", "4", "rav2:create_app()", "-b", "0.0.0.0:8000", "--access-logfile", "-"]
