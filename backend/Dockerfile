FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/data/faiss_index

COPY . .

RUN ls -la /app/data/faiss_index && \
    echo "FAISS index files:" && \
    ls -la /app/data/faiss_index/index*

RUN chmod -R 755 /app/data

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]