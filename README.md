# OpenTrace

OpenTrace is an open-source, fully local tool designed to analyze watch history data (such as Google Takeout for YouTube and TikTok) to uncover filter bubbles and algorithmic manipulation patterns. All processing occurs locally on your machine to ensure strict data privacy.

## Architecture

The project utilizes a hybrid desktop application architecture optimized for memory-constrained environments:

- **Frontend:** Built with HTML, CSS, and JavaScript for an interactive user interface.
- **Backend:** Written in Python to execute evaluation algorithms (concentration, diversity, timeline analysis).
- **Desktop Bridge:** Uses `pywebview` to connect the frontend and backend. It renders the application as a native desktop window using the built-in OS web engine, eliminating the need for a standalone web server.
- **Data Ingestion:** Implements memory-efficient streaming for massive JSON files using `ijson` to prevent RAM exhaustion. It bypasses heavy databases entirely, relying strictly on local caching.
- **LLM Integration:** Connects locally to an Ollama server to run the Gemma 2 model for evaluating algorithmic manipulation patterns.

## Prerequisites

1.  **Python:** Download and install Python 3.10 or higher from the [official Python website](https://www.python.org/downloads/). You must check the "Add python.exe to PATH" box during the installation process.

## Installation & Setup

1.  Clone the repository to your local machine:

    ```bash
    git clone [https://github.com/yourusername/OpenTrace.git](https://github.com/yourusername/OpenTrace.git)
    cd OpenTrace
    ```

2.  Install the required Python dependencies:

    ```bash
    python -m pip install -r requirements.txt
    ```

3.  Launch the application:
    ```bash
    python main.py
    ```

## Project Structure

```text
OpenTrace/
├── .vscode/                 # Editor configuration files
├── .gitignore               # Git ignore rules
├── .python-version          # Python version specification
├── main.py                  # Application entry point and window initialization
└── app/
    ├── __init__.py
    ├── config.py            # Global application settings
    ├── data/                # Static references and cache storage
    │   ├── cache/
    │   │   └── user_profile_cache.json
    │   ├── alternatives.json
    │   └── media_sources.json
    ├── gui/                 # Frontend assets
    │   ├── css/
    │   │   └── style.css
    │   ├── js/
    │   │   ├── app.js
    │   │   └── bridge.js    # Communication bridge between JS and Python
    │   └── index.html
    ├── ingestion/           # Data parsers
    │   ├── __init__.py
    │   ├── dispatcher.py
    │   ├── tiktok_parser.py
    │   └── youtube_parser.py
    ├── llm/                 # Local Ollama connection manager and prompts
    │   ├── __init__.py
    │   ├── ollama_client.py
    │   └── prompts.py
    └── scoring/             # Algorithms for bubble detection and metrics
        ├── __init__.py
        ├── aggregator.py
        ├── concentration.py
        ├── diversity.py
        ├── security.py
        └── timeline.py
```
