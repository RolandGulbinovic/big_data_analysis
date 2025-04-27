FROM python:3.10-slim

WORKDIR /app
RUN mkdir -p /app/output

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY requirements.txt .
COPY main.py .
COPY data/ /app/data/

CMD ["python", "main.py"]