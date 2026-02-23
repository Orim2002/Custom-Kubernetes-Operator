FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY custom_operator.py .
CMD ["kopf", "run", "operator.py", "--all-namespaces"]