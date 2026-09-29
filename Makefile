.PHONY: help install dev-install test lint type-check run clean docker-build docker-run

help:
	@echo "Available commands:"
	@echo "  install        Install production dependencies"
	@echo "  dev-install    Install project in editable mode with development dependencies"
	@echo "  test           Run pytest test suite"
	@echo "  lint           Run ruff linter and formatter checks"
	@echo "  type-check     Run mypy static type checking"
	@echo "  check          Run lint, type-check, and test"
	@echo "  run            Run MCP server"
	@echo "  clean          Remove temporary and cache files"
	@echo "  docker-build   Build Docker container"
	@echo "  docker-run     Run MCP server in Docker container"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check .
	ruff format --check .

lint-fix:
	ruff check --fix .
	ruff format .

type-check:
	mypy src

check: lint type-check test

run:
	python -m payment_mcp.server

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t custom-payment-mcp:latest .

docker-run:
	docker run -i --rm -e MCP_TRANSPORT=stdio custom-payment-mcp:latest
