#!/usr/bin/env bash
# ==========================================================================
# Junta, num relatorio so, tudo que o instrutor precisa para te ajudar.
# Copie a saida inteira e mande para ele.
# ==========================================================================
set -uo pipefail
linha() { echo; echo "==================== $1 ===================="; }

linha "sistema"
uname -a
docker --version 2>&1
docker compose version 2>&1
echo "memoria do Docker: $(( $(docker info --format '{{.MemTotal}}' 2>/dev/null || echo 0) / 1024 / 1024 )) MB"

linha "arquivo .env"
[ -f .env ] && cat .env || echo "(sem .env - usando os padroes)"

linha "containers"
docker ps -a --filter "name=modelagem_" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

linha "tabelas do OLTP"
docker exec modelagem_oltp psql -U sudoers -d liga_sudoers -c '\dt public.*' 2>&1 | head -30

linha "tabelas do DW"
docker exec modelagem_dw psql -U sudoers -d liga_sudoers_dw -c '\dt public.*' 2>&1 | head -30

linha "conferencia do OLTP"
docker compose run --rm ferramentas python data_simulator/verificador.py oltp 2>&1 | tail -40

linha "conferencia do DW"
docker compose run --rm ferramentas python data_simulator/verificador.py dw 2>&1 | tail -40

for c in modelagem_oltp modelagem_dw modelagem_metabase; do
  linha "ultimas linhas do log: $c"
  docker logs --tail 15 "$c" 2>&1
done
