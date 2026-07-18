# OpenTrace

OpenTrace is a local-first feed transparency app.

## Quick start

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install the dependencies.
4. Start the app.

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Environment variables

The project uses a simple `.env` file for local settings:

```env
ENVIRONMENT=development
DEBUG=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
APP_PORT=8000
```

