# Se construye desde la RAÍZ del proyecto:  docker build -f backend/Dockerfile -t tutor-educa-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Solo lo que el backend necesita (nada de Kivy, KivyMD ni gráficos).
COPY models ./models
COPY services ./services
COPY backend ./backend

RUN useradd --create-home --uid 10001 tutor && mkdir -p /app/datos_backend && chown -R tutor /app
USER tutor

ENV TUTOR_ENTORNO=produccion TUTOR_HOST=0.0.0.0 TUTOR_PUERTO=8000 TUTOR_CONFIAR_PROXY=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/salud', timeout=4).status == 200 else 1)"
CMD ["python", "-m", "backend"]
