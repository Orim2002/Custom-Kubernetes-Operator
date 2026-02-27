FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY custom_operator.py .
COPY metrics.py .
RUN addgroup --system --gid 1000 appgroup && \
    adduser --system --uid 1000 --gid 1000 --no-create-home appuser
USER appuser
CMD ["kopf", "run", "custom_operator.py", "--all-namespaces"]