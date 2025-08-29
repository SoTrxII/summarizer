
#!/usr/bin/env bash
set -ex
echo "Running postCreateCommand..."
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd "$SCRIPT_DIR/../summarizer" && \
poetry config virtualenvs.in-project true && \
poetry install

# Ollama 
ollama pull phi4-mini