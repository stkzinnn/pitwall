# Build multi-stage: a imagem final NÃO tem Node.js nem node_modules, só os
# ficheiros estáticos (HTML/JS/CSS) gerados pelo build, servidos por nginx.
# Isto torna a imagem final muito mais pequena do que se corrêssemos o
# "vite dev" ou o Node dentro do container em produção.

# ---- Stage 1: build ----
# Esta imagem é só usada durante o build; não fica no resultado final.
FROM node:22-alpine AS build

WORKDIR /app

# Copiamos primeiro os ficheiros que descrevem as dependências (não o
# código todo) e instalamos com "npm ci" (instala exatamente o que está no
# package-lock.json, sem tentar atualizar nada — mais previsível que
# "npm install"). Mesma lógica de cache de camadas do backend/Dockerfile:
# esta camada só é reinstalada se package.json/package-lock.json mudarem.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# URL do backend que o FRONTEND (a correr no browser do utilizador) vai
# chamar. É passado como "build arg" porque o Vite substitui
# `import.meta.env.VITE_API_BASE_URL` pelo valor literal durante o
# `npm run build` — o resultado é HTML/JS estático, que já não sabe ler
# variáveis de ambiente depois de gerado (ao contrário do backend, que lê
# o .env em cada arranque). Se precisares de apontar para outro backend,
# tens de voltar a fazer build da imagem com um novo valor, não basta mudar
# uma env var do container em runtime.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---- Stage 2: serve ----
FROM nginx:1.27-alpine AS serve

# Configuração de nginx específica para uma SPA (ver nginx.conf).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiamos só o resultado do build (pasta dist/) do stage anterior — nada
# de node_modules, código-fonte TypeScript, etc. vai parar à imagem final.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
