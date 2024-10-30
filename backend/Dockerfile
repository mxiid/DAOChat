FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/data/faiss_index

COPY app/ /app/app/
COPY data/ /app/data/

RUN echo "Contents of /app/data/faiss_index:" && \
    ls -la /app/data/faiss_index && \
    echo "\nContents of /app/data:" && \
    ls -la /app/data && \
    echo "\nContents of /app:" && \
    ls -la /app

RUN chmod -R 755 /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]