# Makefile for livetranscripts development

.PHONY: help install install-dev test test-unit test-integration test-coverage lint format type-check clean build run

# Default target
help:
	@echo "Available targets:"
	@echo "  install       Install package dependencies"
	@echo "  install-dev   Install package with development dependencies"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-coverage Run tests with coverage report"
	@echo "  lint          Run code linting"
	@echo "  format        Format code with black and isort"
	@echo "  type-check    Run type checking with mypy"
	@echo "  clean         Clean build artifacts and cache"
	@echo "  build         Build the package"
	@echo "  run           Run the application"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest tests/ -m "unit" -v

test-integration:
	pytest tests/ -m "integration" -v

test-coverage:
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -v

test-audio:
	pytest tests/ -m "audio" -v

test-slow:
	pytest tests/ -m "slow" -v

# Code quality
lint:
	flake8 src/ tests/
	@echo "✓ Linting passed"

format:
	black src/ tests/
	isort src/ tests/
	@echo "✓ Code formatted"

type-check:
	mypy src/
	@echo "✓ Type checking passed"

# Quality check pipeline
check: format lint type-check test-unit
	@echo "✓ All quality checks passed"

# Development utilities
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned build artifacts"

build:
	python -m build

# Application
run:
	python -m src.livetranscripts.main

run-server:
	python -m src.livetranscripts.server

dev-run:
	./scripts/dev-run.sh

dev:
	./scripts/dev-run.sh

run-tests-watch:
	pytest-watch tests/ -- -v

# Docker support
docker-build:
	docker build -t livetranscripts .

docker-run:
	docker run -it --rm livetranscripts

# Development environment
dev-setup: install-dev
	pre-commit install
	@echo "✓ Development environment setup complete"

# CI/CD helpers
ci-test: install-dev lint type-check test-coverage
	@echo "✓ CI pipeline completed successfully"