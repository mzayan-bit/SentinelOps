.PHONY: setup train test lint dashboard api

setup:
	bash scripts/setup.sh

train:
	@echo "Training pipeline not yet implemented."

test:
	pytest tests/

lint:
	black src tests
	flake8 src tests

dashboard:
	streamlit run dashboard/experiment_compare.py

api:
	uvicorn inference.api.main:app --host 0.0.0.0 --port 8000 --reload
