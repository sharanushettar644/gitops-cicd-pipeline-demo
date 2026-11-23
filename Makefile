IMAGE ?= sample-api:local

.PHONY: install lint test run docker-build docker-run helm-lint helm-template kind-up kind-down

install:
	cd app && pip install -r requirements-dev.txt

lint:
	cd app && ruff check . && ruff format --check .

test:
	cd app && pytest

run:
	cd app && PYTHONPATH=src uvicorn app.main:app --reload --port 8080

docker-build:
	docker build -t $(IMAGE) app

docker-run:
	docker run --rm -p 8080:8080 $(IMAGE)

helm-lint:
	helm lint helm/sample-api -f helm/sample-api/values-staging.yaml --strict
	helm lint helm/sample-api -f helm/sample-api/values-prod.yaml --strict

helm-template:
	helm template sample-api helm/sample-api -f helm/sample-api/values-prod.yaml

kind-up:
	./scripts/kind-up.sh

kind-down:
	./scripts/kind-down.sh
