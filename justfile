test:
	uv run pytest

test-v:
	uv run pytest -v

test-c:
	uv run pytest --cov=Vimprove --cov-report=term-missing
