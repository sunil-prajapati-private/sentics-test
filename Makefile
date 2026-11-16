.PHONY: help setup doctor up down logs lint test test-e2e review security-review demo-offline demo-safety docs-check
help:
	@grep -E '^[a-z-]+:' Makefile | sed 's/:.*//'
setup:
	@./scripts/dev/setup.sh
doctor:
	@./scripts/dev/doctor.sh
up:
	docker compose up --build
down:
	docker compose down
logs:
	docker compose logs -f
lint:
	cd frontend && npm run lint
test:
	python3 -m unittest discover -s tests -v
test-e2e:
	cd frontend && npm run test:e2e
review:
	@cat harness/code_review/take-home-pdf-gap-review.md
security-review:
	@cat harness/code_review/architecture-review.md
demo-offline:
	./scripts/demo/phase6-offline.sh
demo-safety:
	./scripts/demo/phase6-safety.sh
docs-check:
	git diff --check
