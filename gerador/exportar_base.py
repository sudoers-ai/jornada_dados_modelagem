# -*- coding: utf-8 -*-
"""
Gera modelagem/ddl/legado/02_oltp_dados_base.sql a partir do gerador canonico.

USO (so para quem MANTEM o repositorio; o aluno nunca roda isto):

    docker compose run --rm ferramentas python gerador/exportar_base.py

O arquivo gerado ja esta versionado. Ele carrega no OLTP legado o cadastro
que a empresa ja tinha: categorias, produtos e pessoas. Os PEDIDOS nao
entram aqui: eles sao gerados pelo liga_sudoers_historico.py, depois que o
aluno evoluir a modelagem.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gerador.liga_sudoers_gen import gerar_universo  # noqa: E402

HOJE_GERADOR = datetime(2026, 9, 1, 12, 0, 0)   # o "hoje" fixo do gerador
SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "modelagem", "ddl", "legado", "02_oltp_dados_base.sql")


def q(v):
    return "'" + str(v).replace("'", "''") + "'"


def main():
    u = gerar_universo()   # sempre o universo padrao: semente 42
    with open(SAIDA, "w", encoding="utf-8") as fh:
        w = fh.write
        w("-- ==========================================================================\n")
        w("-- Liga Sudoers - cadastro base do OLTP legado\n")
        w("--\n")
        w("-- GERADO por gerador/exportar_base.py (semente=%d). Nao edite a mao.\n" % u.semente)
        w("-- Sao os mesmos ids dos outros repositorios da Jornada:\n")
        w("-- a pessoa 1 daqui e a pessoa 1 do jornada_dados e do jornada_dados_nosql.\n")
        w("--\n")
        w("-- Os PEDIDOS nao estao aqui. Eles chegam pelo liga_sudoers_historico.py,\n")
        w("-- depois que voce evoluir a modelagem.\n")
        w("-- ==========================================================================\n\n")

        w("-- %d categorias\n" % len(u.categorias))
        for c in u.categorias:
            w("INSERT INTO public.categorias (id, descricao) VALUES (%d, %s);\n"
              % (c["id"], q(c["descricao"])))
        w("SELECT setval('public.categorias_id_seq', %d);\n\n" % len(u.categorias))

        w("-- %d produtos\n" % len(u.produtos))
        for p in u.produtos:
            w("INSERT INTO public.produtos (id, id_categoria, descricao, valor_unit) VALUES (%d, %d, %s, %s);\n"
              % (p["id"], p["id_categoria"], q(p["descricao"]), p["valor_unit"]))
        w("SELECT setval('public.produtos_id_seq', %d);\n\n" % len(u.produtos))

        w("-- %d pessoas (created_at relativo a hoje: clientes antigos)\n" % len(u.pessoas))
        for p in u.pessoas:
            dias = (HOJE_GERADOR - datetime.fromisoformat(p["created_at"])).days
            w("INSERT INTO public.pessoas (id, nome, sexo, dt_nasc, created_at, updated_at) "
              "VALUES (%d, %s, %s, %s, now() - interval '%d days', now() - interval '%d days');\n"
              % (p["id"], q(p["nome"]), q(p["sexo"]), q(p["dt_nasc"]), dias, dias))
    print("escrito:", SAIDA)
    print("  categorias=%d produtos=%d pessoas=%d" % (len(u.categorias), len(u.produtos), len(u.pessoas)))
    print("  pessoa 1 =", u.pessoas[0]["nome"])


if __name__ == "__main__":
    main()
