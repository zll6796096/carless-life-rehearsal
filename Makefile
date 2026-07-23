.PHONY: check-docs dev test backend-test backend-lint frontend-test frontend-build frontend-lint deploy-cloud-run git-deploy

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

test: check-docs
	$(MAKE) backend-test
	$(MAKE) backend-lint
	$(MAKE) frontend-test
	$(MAKE) frontend-build
	$(MAKE) frontend-lint

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

git-deploy:
	chmod +x scripts/git-deploy.sh
	bash scripts/git-deploy.sh


