.PHONY: docs-check docs-test verify

docs-check:
	python earthquake/scripts/check_docs.py

docs-test:
	python earthquake/scripts/test_docs.py

verify:
	python -m earthquake.verify
