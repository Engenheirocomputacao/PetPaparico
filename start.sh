#!/bin/bash
# Servidor Django (frontend em templates HTML)

PORT=${1:-8000}

echo "Limpando processos na porta $PORT..."
fuser -k $PORT/tcp 2>/dev/null

echo "Iniciando Pet Paparico (Django)..."
echo "Acesse: http://localhost:$PORT/"
cd server_django && ../.venv/bin/python3 manage.py runserver 0.0.0.0:$PORT
