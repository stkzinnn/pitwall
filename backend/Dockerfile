# Imagem base "slim": Python oficial sem as ferramentas de compilação e
# bibliotecas gráficas da imagem completa. Muito mais pequena, e chega para
# uma app FastAPI que não compila nada em C.
FROM python:3.11-slim

# PYTHONDONTWRITEBYTECODE: não gerar ficheiros .pyc (inúteis num container
# que é recriado a cada deploy, só ocupam espaço).
# PYTHONUNBUFFERED: os prints/logs do Python vão diretos para o stdout sem
# ficar em buffer — importante em containers, senão os logs só aparecem
# em blocos, com atraso, no "docker compose logs".
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# --- Camada de dependências ---
# Copiamos SÓ o requirements.txt primeiro e instalamos antes de copiar o
# resto do código. O Docker guarda cada instrução em cache ("layer"); se o
# requirements.txt não mudar, esta camada de "pip install" é reaproveitada
# em builds seguintes mesmo que o código da app tenha mudado — evita
# reinstalar ~15 dependências (fastapi, fastf1, sqlalchemy, ...) sempre que
# editas um ficheiro .py.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Camada de código ---
# Só agora copiamos o resto do backend (app/, alembic/, alembic.ini, ...).
# Isto fica DEPOIS do pip install de propósito: é a parte que muda mais
# vezes, por isso fica na camada final, que é a única invalidada em cada
# alteração de código.
COPY . .

# A cache do FastF1 (dados de sessões de F1 descarregados, ficam vários MB
# por sessão) vive aqui dentro do container. No docker-compose.yml este
# caminho é montado como volume nomeado, para sobreviver a
# "docker compose down" / recriação do container e não obrigar a
# redescarregar tudo sempre que o backend reinicia.
ENV FASTF1_CACHE_DIR=/app/.cache/fastf1

EXPOSE 8000

# Script de arranque: aplica as migrations da base de dados e só depois
# arranca o servidor. Ver docker-entrypoint.sh para a explicação da escolha.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
