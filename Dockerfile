FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY custom_operator.py .
CMD ["kopf", "run", "custom_operator.py", "--all-namespaces", "--metrics=http://0.0.0.0:8080/metrics"]