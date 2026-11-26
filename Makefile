.PHONY: docs-check docs-test

docs-check:
	python earthquake/scripts/check_docs.py

docs-test:
	python earthquake/scripts/test_docs.py
