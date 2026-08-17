PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest

.PHONY: setup db dev migrate test messages compile

## Crea el entorno virtual e instala las dependencias.
setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	test -f .env || cp .env.example .env

## Levanta Postgres y espera a que acepte conexiones.
db:
	./scripts/db.sh

## Levanta Postgres, aplica migraciones y sirve la aplicación en :8000.
dev: db migrate
	$(PYTHON) manage.py runserver

migrate:
	$(PYTHON) manage.py migrate

test: db
	$(PYTEST)

## Extrae los textos de plantillas y código al catálogo es-CL.
messages:
	$(PYTHON) manage.py makemessages -l es_CL --ignore=.venv

compile:
	$(PYTHON) manage.py compilemessages --ignore=.venv
