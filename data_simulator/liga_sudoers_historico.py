# -*- coding: utf-8 -*-
"""
Gera o HISTORICO de pedidos da Liga Sudoers no banco transacional.

    python data_simulator/liga_sudoers_historico.py [qtde_pedidos] [--limpar]
    (no dia a dia:  make historico)

ESTE SCRIPT E A PROVA DA ETAPA 3.
Antes de gravar qualquer linha ele confere a SUA modelagem contra
modelagem/dbml/02_oltp_evoluido.dbml. Se voce replicou o modelo certo, ele
roda ate o fim. Se nao, ele para e diz exatamente o que falta.

O que ele grava (180 dias de historico, terminando agora):
    - o peso dos produtos                       (Demanda 2)
    - dispositivos e a analise de fraude        (Demanda 1)
    - enderecos, transportadoras, transportes   (Demanda 2)
    - pagamentos e o historico de status        (Demanda 3)
    - e, claro, pedidos, itens e auditoria

E deterministico: com a semente padrao (42), os dados sao sempre os mesmos.
"""
import sys

from functions import *      # noqa: F401,F403  (mesmo padrao do liga_sudoers)


def main():
    argumentos = [a for a in sys.argv[1:] if not a.startswith("--")]
    limpar = "--limpar" in sys.argv
    try:
        total_pedidos = int(argumentos[0])
    except (IndexError, ValueError):
        total_pedidos = N_PEDIDOS_PADRAO

    conn = conectar("oltp")

    # 1) O PORTAO: a modelagem esta igual ao modelo?
    exigir_modelagem(conn, "oltp")

    cursor = conn.cursor()
    universo = gerar_universo(semente=SEMENTE, n_pedidos=total_pedidos)
    conferir_cadastro_base(cursor, universo)

    # 2) Ja existe historico?
    existentes = contar(cursor, "pedidos")
    if existentes and not limpar:
        print("%s✅ O histórico já está carregado%s (%d pedidos no banco). Nada foi alterado."
              % (V, F, existentes))
        print("   Para apagar tudo e gerar de novo: make historico args=--limpar")
        conn.close()
        return 0
    if existentes and limpar:
        print("Apagando os %d pedidos atuais e tudo que depende deles..." % existentes)
        limpar_movimento(cursor, universo)

    # 3) Gera e grava, tudo numa transacao so: ou entra tudo, ou nao entra nada.
    print("Gerando o histórico (semente=%d, %d pedidos)..." % (SEMENTE, total_pedidos))
    extensao = ext_mod.estender(universo)
    agora = datetime.now().replace(microsecond=0)
    try:
        gravado = carregar_historico(cursor, universo, extensao, agora)
        conn.commit()
    except Exception as e:          # noqa: BLE001
        conn.rollback()
        print()
        print("%s❌ O banco recusou a carga. Nada foi gravado.%s" % (R, F))
        print("   Erro do PostgreSQL: %s" % str(e).strip().splitlines()[0])
        print("   Isso costuma ser uma restrição diferente do modelo (tamanho de coluna,")
        print("   CHECK, UNIQUE a mais...). Compare com modelagem/dbml/02_oltp_evoluido.dbml")
        print("   ou aplique a resposta pronta: make gabarito-oltp")
        conn.close()
        return 1

    print()
    for tabela, n in gravado.items():
        print("  %-26s %6d" % (tabela, n))

    cursor.execute("""SELECT status, count(*) FROM public.pedidos GROUP BY 1 ORDER BY 2 DESC""")
    print()
    print("  pedidos por situação: " + ", ".join("%s=%d" % (s, n) for s, n in cursor.fetchall()))
    fraudes = contar(cursor, "auditoria_pedidos", "WHERE is_fraude")
    print("  fraudes confirmadas : %d (%.1f%% dos pedidos)" % (fraudes, 100.0 * fraudes / total_pedidos))
    cursor.execute("SELECT min(dt_venda)::date, max(dt_venda)::date FROM public.pedidos")
    print("  período             : %s até %s" % cursor.fetchone())

    print()
    print("%s✅ Histórico carregado com sucesso.%s Sua modelagem transacional está correta." % (V, F))
    print("   Próximo passo: make streaming ciclos=5")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
