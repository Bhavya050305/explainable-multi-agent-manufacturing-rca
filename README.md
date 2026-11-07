# explainable-multi-agent-manufacturing-rca

Explainable multi-agent AI system for manufacturing anomaly detection, failure-risk prediction and root cause analysis, with cited evidence and human-in-the-loop approval.

## Status

| Phase | Scope | State |
|---|---|---|
| 1 | Synthetic data generators, database schema, seeding | Done |
| 2 | Isolation Forest, LSTM autoencoder, sensor attribution, Kernel SHAP, ResNet defect classifier | Done |
| 2 (step 5) | Supervised failure-risk regression | Closed as a feasibility assessment (no-go) |
| 3 | Supervisor and specialist agents, MCP server, RAG over SOPs, ticket approval, frontend | Not started |

All results so far come from a synthetic 10-machine dataset. They show that the pipeline works, not that it generalizes to a real plant.

## Layout

```
backend/app/ml/        models, preprocessing, attribution and SHAP code
backend/tests/         pytest suite
ml/data_generator/     synthetic sensor, maintenance and image generators
data/                  raw/processed data and seed script
reports/               experiment and audit reports
```

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
make setup
make data
make preprocess
make train
make test
```

`make help` lists every target.
