.DEFAULT_GOAL := all

MYSQL = docker compose exec -T mysql sh -c 'mysql -u"$$MYSQL_USER" -p"$$MYSQL_PASSWORD" "$$MYSQL_DATABASE"'

.PHONY: all download db db-schema db-load db-derive sections test

all: download db sections test

download:
	python -m sectra.ingestion.download
	python -m sectra.ingestion.dataset_report

db-schema:
	$(MYSQL) < sql/schema.sql

db-load:
	python -m sectra.ingestion.load_manifests
	python -m sectra.ingestion.xbrl_loader
	python -m sectra.ingestion.load_metric_map

db-derive:
	$(MYSQL) < sql/views.sql
	$(MYSQL) < sql/post_load.sql

db: db-schema db-load db-derive

sections:
	python -m sectra.parsing.build_sections

test:
	pytest -q