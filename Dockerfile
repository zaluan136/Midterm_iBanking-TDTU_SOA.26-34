FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home appuser
COPY --chown=appuser:appuser services ./services
COPY --chown=appuser:appuser web ./web
COPY --chown=appuser:appuser databases/sql ./databases/sql
COPY --chown=appuser:appuser databases/migrations ./databases/migrations
COPY --chown=appuser:appuser tests ./tests
COPY --chown=appuser:appuser apply_schema_updates.py seed_demo.py ./
USER appuser
EXPOSE 8000
CMD ["uvicorn", "services.gateway:app", "--host", "0.0.0.0", "--port", "8000"]
