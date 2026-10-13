# Caixa de ferramentas da disciplina de Modelagem.
# Um unico container com Python + drivers. O aluno NAO instala nada na
# maquina: todo script roda aqui dentro, via `make` ou `docker compose run`.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
CMD ["python", "-c", "print('Caixa de ferramentas pronta. Veja `make ajuda`.')"]
