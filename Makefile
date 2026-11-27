ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif

.PHONY: docs-check docs-test test verify

docs-check:
	$(PYTHON) earthquake/scripts/check_docs.py

docs-test:
	$(PYTHON) earthquake/scripts/test_docs.py

verify:
	$(PYTHON) -m earthquake.verify

# Every unit test module (earthquake/ is a namespace package, so list the modules explicitly).
TESTS := $(basename $(subst /,.,$(wildcard earthquake/test_*.py)))

test:
	$(PYTHON) -m unittest $(TESTS)
