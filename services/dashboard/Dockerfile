FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY services/dashboard/requirements.txt .
RUN pip install --no-cache-dir \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org \
        -r requirements.txt

COPY services/dashboard/app.py ./app.py
COPY services/dashboard/home.py ./home.py
COPY services/dashboard/theme.py ./theme.py
COPY services/dashboard/common.py ./common.py
COPY services/dashboard/pages ./pages
COPY services/dashboard/.streamlit ./.streamlit

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
