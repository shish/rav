Install:
```
mkdir data
echo "Some secret thing" > data/secret.txt
uv run flask --app rav2 init-db
```

Run:
```
uv run flask --app rav2 --debug run
```

Test:
```
uv run ruff format
uv run ruff check
uv run pytest
uv run ty check
```
