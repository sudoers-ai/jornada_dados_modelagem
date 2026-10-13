# -*- coding: utf-8 -*-
"""
Guia de evidencias automatico:  make validar

Confere, item por item, se o que esta nos bancos e coerente:

  TRANSACIONAL  a modelagem bate com o modelo; o historico bate com o
                gerador (mesma semente = mesmos numeros); os dados sao
                integros entre as tabelas novas e as antigas.

  DIMENSIONAL   a modelagem bate com o modelo; e o que o ETL carregou no DW
                fecha com a fotografia (staging) que ele tirou do
                transacional. E a prova de que nada foi perdido nem contado
                em dobro na transformacao.

Cada linha e um ✅ ou um ❌ com o numero esperado e o encontrado. O que
ainda nao foi feito na trilha aparece como "pulado", nao como erro.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "data_simulator"))

from functions import (A, C, F, N, N_PEDIDOS_PADRAO, R, SEMENTE, V,        # noqa: E402
                       conectar, ext_mod, gerar_universo)
from verificador import conferir                                           # noqa: E402

passou = falhou = 0


def checar(descricao, ok, detalhe=""):
    global passou, falhou
    if ok:
        passou += 1
        print("  %s✅%s %s %s%s%s" % (V, F, descricao, C, detalhe, F))
    else:
        falhou += 1
        print("  %s❌%s %s %s%s%s" % (R, F, descricao, N, detalhe, F))


def um(cur, sql):
    cur.execute(sql)
    return cur.fetchone()[0]


def igual(descricao, encontrado, esperado):
    checar(descricao, encontrado == esperado,
           "(%s)" % esperado if encontrado == esperado
           else "esperado %s, encontrado %s" % (esperado, encontrado))


def validar_oltp():
    print()
    print("%sTRANSACIONAL (OLTP)%s" % (N, F))
    conn = conectar("oltp")
    cur = conn.cursor()

    pend, _, resumo = conferir(cur, "oltp")
    checar("modelagem igual ao modelo (02_oltp_evoluido.dbml)", not pend,
           "(%d tabelas, %d FKs)" % (resumo["tabelas"], resumo["fks"]) if not pend
           else "%d pendência(s) - rode: make conferir-oltp" % len(pend))
    if pend:
        print("  %s⏭  restante do transacional pulado: termine a etapa 3 primeiro%s" % (A, F))
        conn.close()
        return False

    u = gerar_universo(semente=SEMENTE, n_pedidos=N_PEDIDOS_PADRAO)
    cur.execute("SELECT nome FROM pessoas WHERE id = 1")
    linha = cur.fetchone()
    checar("pessoa id=1 é a mesma do gerador", bool(linha) and linha[0] == u.pessoas[0]["nome"],
           "(%s)" % u.pessoas[0]["nome"])

    pedidos = um(cur, "SELECT count(*) FROM pedidos")
    if pedidos == 0:
        print("  %s⏭  histórico ainda não carregado: rode `make historico`%s" % (A, F))
        conn.close()
        return False

    esperado = ext_mod.resumo(u, ext_mod.estender(u))
    tabelas = ("categorias", "produtos", "pessoas", "enderecos", "dispositivos", "transportadoras",
               "pedidos", "itens_pedidos", "auditoria_pedidos", "pagamentos", "status_pedidos",
               "transportes", "carga_pedidos")
    so_historico = pedidos == esperado["pedidos"]
    if so_historico:
        for t in tabelas:
            igual("%s tem as linhas do gerador" % t, um(cur, "SELECT count(*) FROM %s" % t), esperado[t])
        igual("fraudes confirmadas", um(cur, "SELECT count(*) FROM auditoria_pedidos WHERE is_fraude"),
              esperado["fraudes_confirmadas"])
    else:
        print("  %sℹ️  o streaming já rodou (%d pedidos além do histórico): conferindo os mínimos%s"
              % (C, pedidos - esperado["pedidos"], F))
        for t in tabelas:
            n = um(cur, "SELECT count(*) FROM %s" % t)
            checar("%s tem pelo menos as linhas do histórico" % t, n >= esperado[t],
                   "(%d >= %d)" % (n, esperado[t]) if n >= esperado[t]
                   else "esperado >= %d, encontrado %d" % (esperado[t], n))

    igual("todo produto tem peso", um(cur, "SELECT count(*) FROM produtos WHERE peso_gramas IS NULL"), 0)
    igual("todo pedido tem auditoria",
          um(cur, "SELECT count(*) FROM pedidos p WHERE NOT EXISTS "
                  "(SELECT 1 FROM auditoria_pedidos a WHERE a.id_pedido = p.id)"), 0)
    igual("todo pedido tem pagamento",
          um(cur, "SELECT count(*) FROM pedidos p WHERE NOT EXISTS "
                  "(SELECT 1 FROM pagamentos g WHERE g.id_pedido = p.id)"), 0)
    igual("todo pedido tem endereço de entrega",
          um(cur, "SELECT count(*) FROM pedidos WHERE id_endereco_entrega IS NULL"), 0)
    igual("o status do pedido é o último evento do histórico de status",
          um(cur, """SELECT count(*) FROM pedidos p
                     JOIN LATERAL (SELECT status FROM status_pedidos s WHERE s.id_pedido = p.id
                                   ORDER BY dt_evento DESC, created_at DESC LIMIT 1) u ON true
                     WHERE u.status <> p.status"""), 0)
    igual("o valor do pedido é a soma dos itens",
          um(cur, """SELECT count(*) FROM pedidos p
                     JOIN (SELECT id_pedido, sum(valor_total) AS soma FROM itens_pedidos GROUP BY 1) i
                       ON i.id_pedido = p.id
                     WHERE abs(i.soma - p.valor_total) > 0.01"""), 0)
    igual("toda pessoa tem exatamente 1 endereço principal",
          um(cur, """SELECT count(*) FROM pessoas p
                     WHERE (SELECT count(*) FROM enderecos e
                            WHERE e.id_pessoa = p.id AND e.is_principal) <> 1"""), 0)
    igual("pedido enviado ou entregue está em algum transporte",
          um(cur, """SELECT count(*) FROM pedidos p WHERE p.status IN ('enviado', 'entregue')
                     AND NOT EXISTS (SELECT 1 FROM carga_pedidos c WHERE c.id_pedido = p.id)"""), 0)
    igual("fraude confirmada tem motivo e data",
          um(cur, """SELECT count(*) FROM auditoria_pedidos
                     WHERE is_fraude AND (motivo_fraude IS NULL OR dt_fraude IS NULL)"""), 0)
    conn.close()
    return True


def validar_dw():
    print()
    print("%sDIMENSIONAL (DW)%s" % (N, F))
    conn = conectar("dw")
    cur = conn.cursor()

    pend, _, resumo = conferir(cur, "dw")
    if pend:
        print("  %s⏭  pulado: o DW ainda não está na modelagem nova (%d pendências). "
              "Isso é esperado até a etapa 6.%s" % (A, len(pend), F))
        conn.close()
        return
    checar("modelagem igual ao modelo (04_dw_evoluido.dbml)", True,
           "(%d tabelas, %d FKs)" % (resumo["tabelas"], resumo["fks"]))

    tem_stg = um(cur, "SELECT count(*) FROM information_schema.tables "
                      "WHERE table_schema = 'stg' AND table_name = 'pedidos'")
    if not tem_stg or um(cur, "SELECT count(*) FROM fato_pedidos") == 0:
        print("  %s⏭  ETL novo ainda não rodou: rode `make etl`%s" % (A, F))
        conn.close()
        return

    print("  %s(comparando o DW com a fotografia que o ETL tirou do transacional)%s" % (C, F))
    igual("dim_tempo cobre todas as datas de venda",
          um(cur, """SELECT count(*) FROM stg.pedidos p WHERE NOT EXISTS
                     (SELECT 1 FROM dim_tempo t WHERE t.data = p.dt_venda::date)"""), 0)
    igual("dim_localidade tem as 27 UFs", um(cur, "SELECT count(*) FROM dim_localidade"), 27)
    igual("dim_produtos: 1 linha por produto",
          um(cur, "SELECT count(*) FROM dim_produtos"), um(cur, "SELECT count(*) FROM stg.produtos"))
    igual("dim_dispositivo: 1 linha por aparelho",
          um(cur, "SELECT count(*) FROM dim_dispositivo"), um(cur, "SELECT count(*) FROM stg.dispositivos"))
    n = um(cur, "SELECT count(*) FROM dim_dispositivo WHERE is_compartilhado")
    checar("dim_dispositivo encontrou os anéis de fraude", n >= 6, "(%d aparelhos compartilhados)" % n)
    igual("dim_pessoas: 1 versão ATUAL por pessoa",
          um(cur, "SELECT count(*) FROM dim_pessoas WHERE is_atual"), um(cur, "SELECT count(*) FROM stg.pessoas"))
    igual("dim_pessoas: 1 versão por endereço (SCD 2)",
          um(cur, "SELECT count(*) FROM dim_pessoas"), um(cur, "SELECT count(*) FROM stg.enderecos"))
    igual("dim_pessoas: versões da mesma pessoa não se sobrepõem",
          um(cur, """SELECT count(*) FROM dim_pessoas a JOIN dim_pessoas b
                     ON a.id = b.id AND a.sk_pessoa < b.sk_pessoa
                     AND a.dt_inicio < COALESCE(b.dt_fim, 'infinity')
                     AND b.dt_inicio < COALESCE(a.dt_fim, 'infinity')"""), 0)

    igual("fato_pedidos: 1 linha por item de pedido",
          um(cur, "SELECT count(*) FROM fato_pedidos"), um(cur, "SELECT count(*) FROM stg.itens_pedidos"))
    igual("fato_pedidos: faturamento igual ao do transacional (nada em dobro)",
          um(cur, "SELECT sum(valor_total) FROM fato_pedidos"), um(cur, "SELECT sum(valor_total) FROM stg.pedidos"))
    igual("fato_pedidos: mesmas fraudes do transacional",
          um(cur, "SELECT count(DISTINCT id_pedido) FROM fato_pedidos WHERE is_fraude"),
          um(cur, "SELECT count(*) FROM stg.auditoria_pedidos WHERE is_fraude"))
    igual("fato_entregas: 1 linha por pedido embarcado",
          um(cur, "SELECT count(*) FROM fato_entregas"), um(cur, "SELECT count(*) FROM stg.carga_pedidos"))
    na_fato = um(cur, "SELECT sum(valor_frete) FROM fato_entregas")
    no_oltp = um(cur, "SELECT sum(valor_frete) FROM stg.transportes")
    linhas = um(cur, "SELECT count(*) FROM fato_entregas")
    # cada linha arredonda no maximo meio centavo: a folga e 1 centavo por linha
    checar("fato_entregas: o rateio do frete fecha com o que foi pago",
           abs(float(na_fato) - float(no_oltp)) <= 0.01 * linhas,
           "(fato %s x transacional %s; a diferença é arredondamento)" % (na_fato, no_oltp))
    igual("fato_ciclo_pedido: 1 linha por pedido",
          um(cur, "SELECT count(*) FROM fato_ciclo_pedido"), um(cur, "SELECT count(*) FROM stg.pedidos"))
    igual("fato_ciclo_pedido: status igual ao do transacional",
          um(cur, """SELECT count(*) FROM fato_ciclo_pedido f JOIN stg.pedidos p ON p.id = f.id_pedido
                     WHERE f.status_atual <> p.status"""), 0)
    igual("fato_peso_diario: o agregado fecha com a fato_entregas",
          um(cur, "SELECT sum(peso_total_gramas) FROM fato_peso_diario"),
          um(cur, "SELECT sum(peso_gramas) FROM fato_entregas"))
    conn.close()


def main():
    validar_oltp()
    validar_dw()
    print()
    cor = V if falhou == 0 else R
    print("%s%d passaram, %d falharam%s" % (cor, passou, falhou, F))
    print()
    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
