.PHONY: check-docs dev test hakusan-data-test hakusan-data-evidence hakusan-otp-test hakusan-otp-fetch hakusan-otp-evidence backend-test backend-lint frontend-test frontend-build frontend-lint deploy-cloud-run deploy-config-test git-deploy

HAKUSAN_GTFS_ZIP ?= data/external/hakusan/feed.zip
HAKUSAN_VALIDATOR_REPORT ?= data/external/hakusan/validator/report.json
HAKUSAN_OTP_DIR ?= data/external/hakusan/otp
HAKUSAN_OTP_OSM ?= $(HAKUSAN_OTP_DIR)/hakusan-20260903-canonical.osm
HAKUSAN_OTP_JAR ?= $(HAKUSAN_OTP_DIR)/otp-shaded-2.9.0.jar
HAKUSAN_OTP_WORK_DIR ?= $(HAKUSAN_OTP_DIR)/evidence-runs
HAKUSAN_OTP_SUMMARY ?= data/hakusan/otp-validation-summary.json
HAKUSAN_OTP_PORT ?= 18081
HAKUSAN_OTP_STARTUP_TIMEOUT ?= 120
HAKUSAN_OTP_BUILD_TIMEOUT ?= 600

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

test: check-docs hakusan-data-test hakusan-otp-test
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

hakusan-otp-test:
	python3 -m unittest \
		scripts/test_prepare_hakusan_osm.py \
		scripts/test_prepare_hakusan_otp.py \
		scripts/test_hakusan_otp_contract.py \
		scripts/test_fetch_hakusan_otp_inputs.py \
		scripts/test_run_hakusan_otp_evidence.py
	python3 scripts/validate_hakusan_otp_contract.py
	bash scripts/test_hakusan_otp_docs.sh

hakusan-otp-fetch:
	python3 scripts/fetch_hakusan_otp_inputs.py \
		--repo-root . \
		--output-dir "$(HAKUSAN_OTP_DIR)" \
		--artifact all

hakusan-otp-evidence:
	python3 scripts/run_hakusan_otp_evidence.py \
		--repo-root . \
		--gtfs-zip "$(HAKUSAN_GTFS_ZIP)" \
		--osm "$(HAKUSAN_OTP_OSM)" \
		--otp-jar "$(HAKUSAN_OTP_JAR)" \
		--work-dir "$(HAKUSAN_OTP_WORK_DIR)" \
		--summary-output "$(HAKUSAN_OTP_SUMMARY)" \
		--port "$(HAKUSAN_OTP_PORT)" \
		--startup-timeout "$(HAKUSAN_OTP_STARTUP_TIMEOUT)" \
		--build-timeout "$(HAKUSAN_OTP_BUILD_TIMEOUT)"

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
