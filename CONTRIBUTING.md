# Contributing to Artha AI

## Development Setup
```bash
git clone https://github.com/Gaurav711/artha-ai.git
cd artha-ai
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in your GROQ_API_KEY and other values

# Train model and ingest regulations
python scripts/train_fraud_model.py
python scripts/ingest_regulations.py

# Run tests
pytest --cov=app -v

# Run locally
uvicorn app.main:app --reload --port 7860
```

## Pull Request Guidelines
- All PRs must pass `ruff check app/` and `mypy app/`
- Test coverage must not drop below 80%
- Security-sensitive changes require a description of the threat model
