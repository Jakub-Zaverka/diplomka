FROM python:3.12-slim

# pracovní složka uvnitř kontejneru
WORKDIR /app

# nainstaluj knihovny
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# zkopíruj celý projekt
COPY . .

# proměnné prostředí


# otevři port
EXPOSE 5000

# spusť Flask přes Waitress
CMD ["python", "-c", "import app; app.run_waitress()"]
