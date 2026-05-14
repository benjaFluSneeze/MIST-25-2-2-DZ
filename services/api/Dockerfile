FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY services/api/requirements.txt .
RUN pip install --no-cache-dir \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org \
        -r requirements.txt

COPY services/api/src ./src
COPY ml/features.py ./ml/features.py
COPY ml/__init__.py ./ml/__init__.py

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
