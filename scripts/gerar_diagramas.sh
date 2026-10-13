#!/usr/bin/env bash
# ==========================================================================
# Regenera as imagens de modelagem/img/ a partir dos arquivos .dbml.
#
# So para quem MANTEM o repositorio (o aluno nao precisa disto): rode depois
# de alterar qualquer arquivo de modelagem/dbml/. Precisa de Node.js.
# ==========================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
for arquivo in modelagem/dbml/*.dbml; do
  nome=$(basename "$arquivo" .dbml)
  npx -y @softwaretechnik/dbml-renderer -i "$arquivo" -o "modelagem/img/$nome.svg"
  echo "  ✅ modelagem/img/$nome.svg"
done
