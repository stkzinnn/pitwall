#!/bin/sh
# Corre sempre que o container do backend arranca (docker compose up,
# restart, redeploy, ...).
#
# Porquê aqui e não um serviço "migrate" separado no docker-compose?
# Para um projeto deste tamanho, ter as migrations a correr automaticamente
# antes do servidor é mais simples de operar (um único "docker compose up"
# nunca falha por a BD estar desatualizada) e o "alembic upgrade head" é
# idempotente — se já não houver migrations novas por aplicar, não faz nada.
# Num sistema maior/em produção a sério, preferir-se-ia um passo de deploy
# separado (para não correr migrations em paralelo se houver várias réplicas
# do backend a arrancar ao mesmo tempo), mas não é o caso aqui.
set -e

echo "[entrypoint] A aplicar migrations (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] A arrancar uvicorn..."
# exec substitui o processo do shell pelo do uvicorn (em vez de o correr
# como filho) — sinais como Ctrl+C / "docker stop" chegam diretamente ao
# uvicorn, que faz shutdown limpo, em vez de ficarem presos no shell.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
