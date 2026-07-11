.PHONY: help install dev test lint build up down

help:
	@echo "install  - install backend + frontend deps"
	@echo "dev      - run backend (8000) and frontend (5173) locally"
	@echo "test     - run backend tests"
	@echo "lint     - ruff check backend"
	@echo "up/down  - docker compose up/down"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app

build:
	cd frontend && npm run build

up:
	docker compose up --build

down:
	docker compose down
