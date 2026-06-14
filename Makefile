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
	@echo "Dashboard not yet implemented."
	# streamlit run src/app.py

api:
	@echo "API not yet implemented."
	# uvicorn src.main:app --reload
