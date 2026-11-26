ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif

.PHONY: docs-check docs-test verify

docs-check:
	$(PYTHON) earthquake/scripts/check_docs.py

docs-test:
	$(PYTHON) earthquake/scripts/test_docs.py

verify:
	$(PYTHON) -m earthquake.verify
