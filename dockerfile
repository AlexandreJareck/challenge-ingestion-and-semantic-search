FROM python:3.11-slim
WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv sync --no-dev

COPY src/ ./src/
COPY data/ ./data/

ENV PYTHONPATH=/app/src
CMD ["uv", "run", "python", "src/chat.py"]