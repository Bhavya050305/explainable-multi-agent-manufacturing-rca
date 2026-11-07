.PHONY: setup data seed preprocess train evaluate test clean help

# Phase 1-2 targets only. The agents, MCP server and frontend are Phase 3 and
# do not exist in the repository yet, so no target refers to them.

help:
	@echo "ManuMind AI - Available Make Targets:"
	@echo "  make setup       - Install backend dependencies"
	@echo "  make data        - Generate synthetic sensors, maintenance records and defect images"
	@echo "  make seed        - Load generated data into the database"
	@echo "  make preprocess  - Scale sensor data and build sequence windows"
	@echo "  make train       - Train Isolation Forest, LSTM autoencoder and ResNet defect classifier"
	@echo "  make evaluate    - Evaluate trained models and regenerate reports"
	@echo "  make test        - Run the pytest suite in backend/tests"
	@echo "  make clean       - Remove Python cache folders"

setup:
	python -m pip install -r backend/requirements.txt

data:
	python ml/data_generator/generate_sensor_data.py
	python ml/data_generator/generate_maintenance.py
	python ml/data_generator/generate_defect_images.py
	python ml/data_generator/generate_stats_report.py

seed:
	python data/seed.py

preprocess:
	python -m backend.app.ml.preprocessing.sensor_preprocessing

train:
	python -m backend.app.ml.isolation_forest.train
	python -m backend.app.ml.lstm_autoencoder.train
	python -m backend.app.ml.defect_classifier.train

evaluate:
	python -m backend.app.ml.isolation_forest.evaluate
	python -m backend.app.ml.lstm_autoencoder.evaluate
	python -m backend.app.ml.sensor_attribution.evaluate
	python -m backend.app.ml.shap_explainability.evaluate
	python -m backend.app.ml.defect_classifier.evaluate

test:
	python -m pytest backend/tests -v

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
