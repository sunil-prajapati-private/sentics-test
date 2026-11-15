.PHONY: help setup doctor up down logs lint test test-integration test-e2e review security-review demo-happy demo-offline demo-safety docs-check
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
lint test test-integration test-e2e review security-review demo-happy demo-offline demo-safety docs-check:
	@echo "$@ is defined for later phases; see commands/$@.md"
