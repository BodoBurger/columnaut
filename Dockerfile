FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system columnaut \
    && useradd --system --gid columnaut --create-home columnaut

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip \
    && python -m pip install .

COPY .streamlit ./.streamlit
COPY app.py ./app.py

USER columnaut

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"]

CMD ["streamlit", "run", "app.py"]

