.PHONY: check-docs dev test hakusan-data-test hakusan-data-evidence backend-test backend-lint frontend-test frontend-build frontend-lint deploy-cloud-run deploy-config-test git-deploy

HAKUSAN_GTFS_ZIP ?= data/external/hakusan/feed.zip
HAKUSAN_VALIDATOR_REPORT ?= data/external/hakusan/validator/report.json

REQUIRED_DOCS := README.md \
	docs/product-blueprint.md \
	docs/architecture.md \
	docs/data-policy.md \
	docs/open-data-challenge-2026-fit.md \
	docs/demo-script-ja.md \
	docs/demo-script-zh.md \
	docs/submission-summary-ja.md \
	docs/technical-notes.md

check-docs:
	@test -d frontend
	@test -d backend
	@test -d docs
	@for file in $(REQUIRED_DOCS); do test -s "$$file"; done
	@grep -q "車なし生活リハーサル" README.md
	@grep -q "not a generic route planner" README.md
	@grep -q "判定不能" docs/data-policy.md
	@grep -q "Open Data Challenge" docs/open-data-challenge-2026-fit.md
	@grep -q "高齢者" docs/submission-summary-ja.md
	@echo "Prompt 0 docs and structure checks passed."

dev:
	docker compose up --build

test: check-docs hakusan-data-test
	$(MAKE) backend-test
	$(MAKE) backend-lint
	$(MAKE) frontend-test
	$(MAKE) frontend-build
	$(MAKE) frontend-lint

hakusan-data-test:
	python3 -m unittest scripts/test_validate_hakusan_data.py
	python3 scripts/validate_hakusan_data.py
	bash scripts/test_hakusan_docs.sh

hakusan-data-evidence:
	python3 scripts/validate_hakusan_data.py --require-evidence \
		--gtfs-zip "$(HAKUSAN_GTFS_ZIP)" \
		--validator-report "$(HAKUSAN_VALIDATOR_REPORT)"

backend-test:
	cd backend && uv run pytest

backend-lint:
	cd backend && uv run ruff check .

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

deploy-cloud-run:
	bash scripts/deploy-cloud-run.sh

deploy-config-test:
	python3 -m unittest scripts/test_release_state.py
	bash scripts/test_cloudbuild_config.sh

git-deploy:
	chmod +x scripts/git-deploy.sh
	bash scripts/git-deploy.sh
