FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
	git \
	curl \
	&& rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

RUN mkdir -p /app/vimprove-cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
	CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "api.py", "--host", "0.0.0.0", "--port", "8000"]
