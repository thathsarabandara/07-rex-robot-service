.PHONY: help install lint format test coverage clean docker-build docker-up docker-down

help:
	@echo "Rex Identity Server - Available Commands"
	@echo "===================================="
	@echo "  make install          Install production dependencies"
	@echo "  make lint             Run all linting checks (flake8, isort, black)"
	@echo "  make format           Format code with black and isort"
	@echo "  make test             Run tests with pytest"
	@echo "  make coverage         Run tests with coverage report"
	@echo "  make run              Run development server"
	@echo "  make clean            Remove cache files and directories"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-up        Start Docker containers"
	@echo "  make docker-down      Stop Docker containers"

install:
	pip install -r requirements.txt

lint:
	isort --check-only app tests
	black --check app tests
	flake8 app tests

format:
	isort app tests
	black app tests

test:
	pytest tests/ -v

coverage:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name .coverage -delete

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
