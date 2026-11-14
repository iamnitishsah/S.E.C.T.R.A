.DEFAULT_GOAL := help

MYSQL = docker compose exec -T mysql sh -c 'MYSQL_PWD="$$MYSQL_PASSWORD" mysql -u"$$MYSQL_USER" "$$MYSQL_DATABASE"'
EVAL  = python -m sectra.evaluation.retrieval_eval

.PHONY: help up down all download db db-schema db-load db-derive sections chunks embed index test eval threshold

help:
	@echo "make up         start MySQL and Qdrant"
	@echo "make all        full offline pipeline: download -> db -> sections -> chunks -> embed -> index"
	@echo "make test       unit tests (no network)"
	@echo "make eval       retrieval evaluation, both question sets (needs Qdrant + API keys)"
	@echo "make threshold  refusal-threshold sweep from the saved eval results"
	@echo "make down       stop the containers"

up:
	docker compose up -d

down:
	docker compose down

all: download db sections chunks embed index

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

chunks:
	python -m sectra.ingestion.chunker

embed:
	python -m sectra.ingestion.embed_chunks

index:
	python -m sectra.ingestion.index_chunks

test:
	pytest -q

eval:
	for s in original paraphrased; do \
		for v in dense rerank; do $(EVAL) --variant $$v --set $$s || exit 1; done; \
		$(EVAL) --compare dense rerank --set $$s; \
	done

threshold:
	python -m sectra.evaluation.threshold --variant rerank
	python -m sectra.evaluation.threshold --variant dense
