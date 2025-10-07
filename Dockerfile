# Použij malý Python image
FROM python:3.11-slim

# Nastav pracovní adresář
WORKDIR /app

# Zkopíruj projekt (mimo lokální venv)
COPY . /app

# Nainstaluj závislosti
RUN pip install --no-cache-dir -r requirements.txt

# Fly.io očekává běh na portu 8080
ENV PORT=8080

# Spusť Flask aplikaci přes Gunicorn (lepší než flask run)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
