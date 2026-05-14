FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org \
        -r requirements.txt

COPY src ./src

CMD ["python", "-m", "src.main"]
