.PHONY: setup seed train index dev test build clean help

help:
	@echo "ManuMind AI - Available Make Targets:"
	@echo "  make setup   - Install dependencies for backend and frontend"
	@echo "  make seed    - Generate synthetic data and seed database"
	@echo "  make train   - Train ML models (Isolation Forest, Autoencoder, Failure Classifier)"
	@echo "  make index   - Build RAG vector index over SOPs and incident reports"
	@echo "  make dev     - Run backend and frontend concurrently"
	@echo "  make test    - Run all pytest test suites"
	@echo "  make build   - Build backend and frontend artifacts"
	@echo "  make clean   - Clean cache and temp files"

setup:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm install

seed:
	python data/seed.py

train:
	python ml/training/train_isolation_forest.py
	python ml/training/train_lstm_autoencoder.py
	python ml/training/train_failure_classifier.py
	python ml/training/train_defect_classifier.py
	python ml/evaluate.py

index:
	python knowledge_base/build_index.py

dev:
	python -m uvicorn backend.app.main:app --reload --port 8000 & cd frontend && npm run dev

test:
	pytest backend/tests agents/tests mcp_server/tests -v

build:
	cd frontend && npm run build

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
