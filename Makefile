setup:
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@echo "ثبّت Ollama من https://ollama.com"
	@echo "بعدين شغّل: ollama pull mistral"

run:
	.venv/bin/python main.py

check:
	curl -s http://localhost:11434/api/tags || echo "Ollama مو شغال"

test:
	.venv/bin/python -m pytest tests/ -v

clean:
	rm -rf .venv .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +