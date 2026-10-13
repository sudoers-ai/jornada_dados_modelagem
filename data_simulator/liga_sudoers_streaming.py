# -*- coding: utf-8 -*-
"""
Gera dados CONTINUAMENTE no banco transacional, simulando a operacao viva.

    python data_simulator/liga_sudoers_streaming.py [--ciclos N] [--intervalo S]
    (no dia a dia:  make streaming            -> roda ate o Ctrl+C
                    make streaming ciclos=5   -> roda 5 ciclos e para)

ESTE SCRIPT E A SEGUNDA PROVA DA ETAPA 3. O historico so faz INSERT. Aqui o
banco sofre UPDATE o tempo todo - e e o UPDATE que testa de verdade as
chaves, os valores padrao e os triggers de updated_at.

A cada ciclo, com uma certa chance (o 1o ciclo forca um de cada):
    - chegam clientes e pedidos novos (5% sao fraude, ainda nao confirmada)
    - pagamentos sao aprovados ou recusados          UPDATE pagamentos
    - pedidos sao separados, despachados, entregues  UPDATE pedidos + INSERT status
    - caminhoes saem e chegam                        INSERT/UPDATE transportes
    - fraudes sao confirmadas pelo analista          UPDATE auditoria_pedidos
    - pessoas mudam de endereco                      UPDATE + INSERT enderecos
    - produtos mudam de preco                        UPDATE produtos
"""
import argparse
import sys
import time

from faker import Faker

from functions import *      # noqa: F401,F403  (mesmo padrao do liga_sudoers)

TAXA_FRAUDE = 0.05

# Ritmo da simulacao. O historico tem ~28 pedidos por dia; se o streaming
# despejasse varios pedidos a cada 5 segundos, em meia hora o "hoje" teria
# mais vendas que o mes inteiro e todos os graficos ficariam distorcidos.
# Por isso a chance de cada acontecimento, por ciclo, e baixa. O 1o ciclo
# forca um de cada tipo: e ele que faz deste script uma prova.
CHANCE_PEDIDO = 0.20
CHANCE_CLIENTE = 0.05
CHANCE_MUDANCA = 0.04
CHANCE_PRECO = 0.02


def um_ciclo(conn, cursor, fake, numero, pendentes):
    """Executa um ciclo e devolve a lista de acontecimentos (para o log)."""
    feitos = []
    primeiro = numero == 1          # no 1o ciclo forcamos um de cada: e a prova

    # ----------------------------------------------------- clientes novos
    if primeiro or random.random() < CHANCE_CLIENTE:
        gerar_pessoa(cursor, fake)
        conn.commit()
        feitos.append("+1 cliente")

    # ------------------------------------------------------ pedidos novos
    qtde = 0
    if primeiro or random.random() < CHANCE_PEDIDO:
        qtde = 2 if random.random() < 0.2 else 1
    cursor.execute("SELECT id FROM public.pessoas ORDER BY random() LIMIT %s", (qtde,))
    suspeitos = 0
    for (id_pessoa,) in cursor.fetchall():
        fraude = None
        if (primeiro and suspeitos == 0) or random.random() < TAXA_FRAUDE:
            fraude = random.choice(["geolocalizacao", "troca_dispositivo"])
            suspeitos += 1
        id_pedido = gera_pedido(cursor, fake, id_pessoa, fraude)
        conn.commit()               # um pedido = uma transacao
        if fraude:
            # o analista leva um tempo para confirmar (o 1o e rapido, de proposito)
            espera = 2 if primeiro else random.randint(6, 30)
            pendentes.append({"id_pedido": id_pedido, "motivo": fraude, "ciclo": numero + espera})
    if qtde:
        feitos.append("+%d pedido(s)%s" % (qtde, " (%d suspeito)" % suspeitos if suspeitos else ""))

    # --------------------------------------------------------- pagamentos
    aprovados, recusados = processa_pagamentos(cursor)
    conn.commit()
    if aprovados:
        feitos.append("%d pagamento(s) aprovado(s)" % aprovados)
    if recusados:
        feitos.append("%d recusado(s)" % recusados)

    # ---------------------------------------------------------- separacao
    n = separa_pedidos(cursor, 3 if primeiro else random.choice([0, 0, 1, 1, 2]))
    conn.commit()
    if n:
        feitos.append("%d separado(s)" % n)

    # ---------------------------------------------------------- expedicao
    if primeiro or random.random() < 0.15:
        n = despacha_transporte(cursor)
        conn.commit()
        if n:
            feitos.append("1 caminhão saiu (%d pedidos)" % n)

    # ------------------------------------------------------------ entrega
    if primeiro or random.random() < 0.15:
        n = entrega_transporte(cursor)
        conn.commit()
        if n:
            feitos.append("1 caminhão chegou (%d pedidos entregues)" % n)

    # ---------------------------------------------------------- devolucao
    if primeiro or random.random() < 0.01:
        if devolve_pedido(cursor):
            feitos.append("1 devolução")
        conn.commit()

    # ------------------------------------------------- fraude confirmada
    vencidas = [p for p in pendentes if p["ciclo"] <= numero]
    for p in vencidas:
        pendentes.remove(p)
        if confirma_fraude(cursor, p["id_pedido"], p["motivo"]):
            feitos.append("fraude confirmada no pedido %d (%s)" % (p["id_pedido"], p["motivo"]))
        conn.commit()

    # ------------------------------------------------- mudanca de endereco
    if numero == 2 or random.random() < CHANCE_MUDANCA:
        id_pessoa = muda_endereco(cursor, fake)
        conn.commit()
        if id_pessoa:
            feitos.append("pessoa %d mudou de endereço" % id_pessoa)

    # ---------------------------------------------------- reajuste de preco
    if numero == 3 or random.random() < CHANCE_PRECO:
        feitos.append("produto %d mudou de preço" % reajusta_preco(cursor))
        conn.commit()

    return feitos


def main():
    ap = argparse.ArgumentParser(description="Streaming da Liga Sudoers")
    ap.add_argument("--ciclos", type=int, default=0, help="quantos ciclos rodar (0 = ate o Ctrl+C)")
    ap.add_argument("--intervalo", type=float, default=5.0, help="segundos entre os ciclos")
    args = ap.parse_args()

    conn = conectar("oltp")

    # O PORTAO: a modelagem esta igual ao modelo?
    exigir_modelagem(conn, "oltp")

    cursor = conn.cursor()
    if contar(cursor, "pedidos") == 0:
        print("%s❌ Ainda não existe histórico.%s Rode primeiro: make historico" % (R, F))
        conn.close()
        return 1

    fake = Faker("pt_BR")
    # compras de fora da area atendida que ficaram sem analise viram pendencia
    pendentes = [{"id_pedido": i, "motivo": "geolocalizacao", "ciclo": 4}
                 for i in suspeitas_pendentes(cursor)]

    print("Iniciando geração de dados para Streaming. %s" %
          ("(%d ciclos)" % args.ciclos if args.ciclos else "(Ctrl+C para parar)"))
    numero = calmos = 0
    try:
        while True:
            numero += 1
            feitos = um_ciclo(conn, cursor, fake, numero, pendentes)
            agora = datetime.now().strftime("%H:%M:%S")
            if feitos:
                calmos = 0
                print("%s[%s] ciclo %d%s | %s" % (C, agora, numero, F, " | ".join(feitos)), flush=True)
            else:
                # ciclo sem acontecimento: nao polui o log, mas da sinal de vida
                calmos += 1
                if calmos % 6 == 0:
                    print("%s[%s] ciclo %d | operação calma: %d ciclos sem novidades%s"
                          % (C, agora, numero, calmos, F), flush=True)
            if args.ciclos and numero >= args.ciclos:
                break
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nStreaming interrompido pelo usuário.")
        conn.close()
        return 0
    except Exception as e:          # noqa: BLE001
        conn.rollback()
        print()
        print("%s❌ O streaming parou no ciclo %d: o banco recusou uma operação.%s" % (R, numero, F))
        print("   Erro do PostgreSQL: %s" % str(e).strip().splitlines()[0])
        print("   Compare a sua modelagem com modelagem/dbml/02_oltp_evoluido.dbml")
        print("   ou aplique a resposta pronta: make gabarito-oltp")
        conn.close()
        return 1

    print()
    print("%s✅ Streaming concluído: %d ciclos sem erro.%s" % (V, numero, F))
    print("   INSERTs e UPDATEs passaram em todas as tabelas novas.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
