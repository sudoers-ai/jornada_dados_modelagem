# -*- coding: utf-8 -*-
"""
Funcoes reutilizaveis dos simuladores (historico e streaming).

Mesmo papel do `functions.py` do repo liga_sudoers: tudo que fala com o
banco fica aqui, e os dois scripts so orquestram.

IMPORTANTE: estes scripts gravam em TODAS as tabelas e colunas novas das
tres demandas. E por isso que eles servem de prova: se a sua modelagem
estiver diferente do modelo, eles nao rodam.
"""
import io
import os
import random
import sys
import time
from datetime import datetime, timedelta

import psycopg2

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "data_simulator"))

from gerador import extensao_modelagem as ext_mod          # noqa: E402
from gerador.liga_sudoers_gen import (                     # noqa: E402
    MODELOS_DISPOSITIVO, UF_LEGITIMAS, UF_SUSPEITAS, _device_id, _geo_da_uf,
    _so_do_modelo, _telefone, gerar_universo)
from verificador import config_conexao, exigir_modelagem   # noqa: E402,F401

V, A, R, C, N, F = "\033[92m", "\033[93m", "\033[91m", "\033[90m", "\033[1m", "\033[0m"

SEMENTE = int(os.getenv("SEMENTE", "42"))
N_PEDIDOS_PADRAO = int(os.getenv("N_PEDIDOS", "5000"))

# Ordem que respeita as chaves estrangeiras na hora de limpar
TABELAS_DE_MOVIMENTO = (
    "carga_pedidos", "transportes", "transportadoras", "status_pedidos", "pagamentos",
    "auditoria_pedidos", "itens_pedidos", "pedidos", "enderecos", "dispositivos",
)


# --------------------------------------------------------------------------
# Conexao
# --------------------------------------------------------------------------
def conectar(banco="oltp", limite=60):
    """Conecta esperando o banco terminar de subir, sem despejar traceback."""
    cfg = config_conexao(banco)
    inicio = time.time()
    ultimo = None
    while time.time() - inicio < limite:
        try:
            return psycopg2.connect(**cfg)
        except psycopg2.OperationalError as e:
            ultimo = e
            time.sleep(2)
    print("%s❌ Não consegui conectar em %s/%s.%s" % (R, cfg["host"], cfg["dbname"], F))
    print("   %s" % str(ultimo).strip().splitlines()[-1])
    print("   Os containers estão no ar? Rode: make subir")
    sys.exit(1)


def copiar(cur, tabela, colunas, linhas):
    """COPY e ordens de magnitude mais rapido que INSERT linha a linha."""
    buf = io.StringIO()
    n = 0
    for linha in linhas:
        buf.write("\t".join(
            "\\N" if v is None else str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ")
            for v in linha))
        buf.write("\n")
        n += 1
    buf.seek(0)
    cur.copy_expert("COPY public.%s (%s) FROM STDIN" % (tabela, ", ".join(colunas)), buf)
    return n


def contar(cur, tabela, onde=""):
    cur.execute("SELECT count(*) FROM public.%s %s" % (tabela, onde))
    return cur.fetchone()[0]


# --------------------------------------------------------------------------
# HISTORICO
# --------------------------------------------------------------------------
def conferir_cadastro_base(cur, u):
    """O cadastro legado (categorias, produtos, pessoas) tem que ser o do gerador."""
    problemas = []
    if contar(cur, "categorias") != len(u.categorias):
        problemas.append("categorias")
    if contar(cur, "produtos") != len(u.produtos):
        problemas.append("produtos")
    if contar(cur, "pessoas", "WHERE id <= %d" % len(u.pessoas)) != len(u.pessoas):
        problemas.append("pessoas")
    cur.execute("SELECT nome FROM public.pessoas WHERE id = 1")
    linha = cur.fetchone()
    if not linha or linha[0] != u.pessoas[0]["nome"]:
        problemas.append("pessoa id=1")
    if problemas:
        print("%s❌ O cadastro base do transacional não é o esperado (%s).%s"
              % (R, ", ".join(problemas), F))
        print("   Alguém apagou ou alterou categorias, produtos ou pessoas.")
        print("   Para voltar ao ponto de partida: make reset-oltp (e refaça a etapa 3)")
        sys.exit(1)


def limpar_movimento(cur, u):
    """Apaga pedidos e tudo que depende deles. O cadastro base fica."""
    cur.execute("TRUNCATE TABLE %s RESTART IDENTITY CASCADE"
                % ", ".join("public.%s" % t for t in TABELAS_DE_MOVIMENTO))
    cur.execute("DELETE FROM public.pessoas WHERE id > %s", (len(u.pessoas),))
    cur.execute("UPDATE public.produtos SET peso_gramas = NULL")
    for p in u.produtos:      # o streaming reajusta precos: volta ao original
        cur.execute("UPDATE public.produtos SET valor_unit = %s WHERE id = %s AND valor_unit <> %s",
                    (p["valor_unit"], p["id"], p["valor_unit"]))


def carregar_historico(cur, u, ext, agora):
    """Grava o universo estendido. Devolve {tabela: linhas gravadas}.

    Todas as datas sao deslocadas para que o "hoje" do gerador vire `agora`.
    """
    delta = agora - ext_mod.HOJE_GERADOR

    def d(quando):
        return None if quando is None else quando + delta

    gravado = {}

    # peso dos produtos (coluna nova numa tabela que ja tinha dado)
    for id_produto, peso in ext["pesos"].items():
        cur.execute("UPDATE public.produtos SET peso_gramas = %s WHERE id = %s", (peso, id_produto))
    gravado["produtos (peso_gramas)"] = len(ext["pesos"])

    gravado["dispositivos"] = copiar(
        cur, "dispositivos", ["device_id", "modelo", "sistema", "created_at", "updated_at"],
        ((x["device_id"], x["modelo"], x["sistema"], d(x["created_at"]), d(x["created_at"]))
         for x in ext["dispositivos"]))

    gravado["enderecos"] = copiar(
        cur, "enderecos",
        ["id", "id_pessoa", "logradouro", "cidade", "uf", "cep", "is_principal", "created_at", "updated_at"],
        ((e["id"], e["id_pessoa"], e["logradouro"], e["cidade"], e["uf"], e["cep"],
          e["is_principal"], d(e["created_at"]), d(e["updated_at"])) for e in ext["enderecos"]))

    gravado["transportadoras"] = copiar(
        cur, "transportadoras", ["id", "nome", "cnpj", "custo_por_kg"],
        ((t["id"], t["nome"], t["cnpj"], t["custo_por_kg"]) for t in ext["transportadoras"]))

    def linhas_pedidos():
        for p in u.pedidos:
            e = ext["pedidos"][p["id"]]
            yield (p["id"], p["id_pessoa"], d(e["dt_venda"]), p["valor_total"],
                   e["id_endereco_entrega"], e["status"], d(e["dt_venda"]), d(e["dt_ultimo_evento"]))
    gravado["pedidos"] = copiar(
        cur, "pedidos",
        ["id", "id_pessoa", "dt_venda", "valor_total", "id_endereco_entrega", "status",
         "created_at", "updated_at"], linhas_pedidos())

    def linhas_itens():
        for p in u.pedidos:
            quando = d(ext["pedidos"][p["id"]]["dt_venda"])
            for it in p["itens"]:
                yield (p["id"], it["id_produto"], it["qtde"], it["valor_total"], quando, quando)
    gravado["itens_pedidos"] = copiar(
        cur, "itens_pedidos",
        ["id_pedido", "id_produto", "qtde", "valor_total", "created_at", "updated_at"], linhas_itens())

    def linhas_auditoria():
        for p in u.pedidos:
            a, e = p["auditoria"], ext["pedidos"][p["id"]]
            yield (p["id"], a["dispositivo"], a["geohash"], a["telefone"], a["device_id"], a["uf"],
                   e["fraude_confirmada"], e["motivo_fraude"], d(e["dt_fraude"]),
                   d(e["dt_venda"]), d(e["dt_fraude"] or e["dt_venda"]))
    gravado["auditoria_pedidos"] = copiar(
        cur, "auditoria_pedidos",
        ["id_pedido", "dispositivo", "geohash", "telefone", "device_id", "uf",
         "is_fraude", "motivo_fraude", "dt_fraude", "created_at", "updated_at"], linhas_auditoria())

    gravado["pagamentos"] = copiar(
        cur, "pagamentos",
        ["id", "id_pedido", "forma", "parcelas", "valor", "status", "dt_pagamento", "created_at", "updated_at"],
        ((g["id"], g["id_pedido"], g["forma"], g["parcelas"], g["valor"], g["status"],
          d(g["dt_pagamento"]), d(g["created_at"]), d(g["updated_at"])) for g in ext["pagamentos"]))

    gravado["status_pedidos"] = copiar(
        cur, "status_pedidos", ["id_pedido", "status", "dt_evento", "created_at", "updated_at"],
        ((s["id_pedido"], s["status"], d(s["dt_evento"]), d(s["dt_evento"]), d(s["dt_evento"]))
         for s in ext["status"]))

    gravado["transportes"] = copiar(
        cur, "transportes",
        ["id", "id_transportadora", "placa", "peso_total_gramas", "valor_frete",
         "dt_saida", "dt_entrega_prevista", "dt_entrega", "created_at", "updated_at"],
        ((t["id"], t["id_transportadora"], t["placa"], t["peso_total_gramas"], t["valor_frete"],
          d(t["dt_saida"]), d(t["dt_entrega_prevista"]), d(t["dt_entrega"]),
          d(t["dt_saida"]), d(t["dt_entrega"] or t["dt_saida"])) for t in ext["transportes"]))

    gravado["carga_pedidos"] = copiar(
        cur, "carga_pedidos", ["id_transporte", "id_pedido", "created_at", "updated_at"],
        ((c["id_transporte"], c["id_pedido"], d(c["dt"]), d(c["dt"])) for c in ext["cargas"]))

    # Os ids foram gravados explicitamente: as sequences precisam alcanca-los,
    # senao o proximo INSERT (do streaming) tentaria reusar o id 1.
    for tabela in ("pedidos", "enderecos", "transportadoras", "transportes", "pagamentos"):
        cur.execute("SELECT setval(pg_get_serial_sequence('public.%s', 'id'), "
                    "(SELECT COALESCE(max(id), 1) FROM public.%s))" % (tabela, tabela))
    return gravado


# --------------------------------------------------------------------------
# STREAMING
# --------------------------------------------------------------------------
def registrar_status(cur, id_pedido, status):
    """Muda a situacao ATUAL do pedido e registra o evento no HISTORICO."""
    cur.execute("UPDATE public.pedidos SET status = %s WHERE id = %s", (status, id_pedido))
    cur.execute("""INSERT INTO public.status_pedidos (id_pedido, status, dt_evento)
                   VALUES (%s, %s, now())
                   ON CONFLICT (id_pedido, status) DO UPDATE SET dt_evento = EXCLUDED.dt_evento""",
                (id_pedido, status))


def gerar_pessoa(cur, fake):
    """Um cliente novo, ja com endereco."""
    sexo = random.choice(["M", "F"])
    nome = fake.name_male() if sexo == "M" else fake.name_female()
    dt_nasc = fake.date_of_birth(minimum_age=18, maximum_age=80)
    cur.execute("SELECT COALESCE(max(id), 0) + 1 FROM public.pessoas")
    id_pessoa = cur.fetchone()[0]
    cur.execute("INSERT INTO public.pessoas (id, nome, sexo, dt_nasc) VALUES (%s, %s, %s, %s)",
                (id_pessoa, nome, sexo, dt_nasc))
    gerar_endereco(cur, fake, id_pessoa, random.choice(UF_LEGITIMAS))
    return id_pessoa


def gerar_endereco(cur, fake, id_pessoa, uf):
    cur.execute("""INSERT INTO public.enderecos (id_pessoa, logradouro, cidade, uf, cep, is_principal)
                   VALUES (%s, %s, %s, %s, %s, true) RETURNING id""",
                (id_pessoa, fake.street_address(), fake.city(), uf, fake.postcode()))
    return cur.fetchone()[0]


def endereco_principal(cur, fake, id_pessoa):
    cur.execute("""SELECT id, uf FROM public.enderecos
                   WHERE id_pessoa = %s AND is_principal ORDER BY id DESC LIMIT 1""", (id_pessoa,))
    linha = cur.fetchone()
    if linha:
        return linha
    uf = random.choice(UF_LEGITIMAS)
    return gerar_endereco(cur, fake, id_pessoa, uf), uf


def novo_dispositivo(cur, modelo=None):
    modelo = modelo or random.choice(MODELOS_DISPOSITIVO)
    device_id = _device_id(random)
    cur.execute("INSERT INTO public.dispositivos (device_id, modelo, sistema) VALUES (%s, %s, %s)",
                (device_id, modelo, _so_do_modelo(modelo)))
    return device_id, modelo


def dispositivo_habitual(cur, id_pessoa):
    """O aparelho com que a pessoa mais comprou (sem contar compras fraudulentas)."""
    cur.execute("""SELECT a.device_id, a.dispositivo, a.telefone
                   FROM public.auditoria_pedidos a
                   JOIN public.pedidos p ON p.id = a.id_pedido
                   WHERE p.id_pessoa = %s AND NOT a.is_fraude AND a.device_id IS NOT NULL
                   GROUP BY 1, 2, 3 ORDER BY count(*) DESC LIMIT 1""", (id_pessoa,))
    linha = cur.fetchone()
    if linha:
        return linha
    device_id, modelo = novo_dispositivo(cur)
    return device_id, modelo, _telefone(random)


def gera_pedido(cur, fake, id_pessoa, fraude=None):
    """Um pedido completo: pedido + itens + auditoria + pagamento + status.

    `fraude` pode ser None, 'geolocalizacao' ou 'troca_dispositivo'. O pedido
    fraudulento NASCE com is_fraude = false: a fraude so e confirmada depois,
    por um UPDATE - como acontece na vida real.
    """
    id_endereco, uf_casa = endereco_principal(cur, fake, id_pessoa)
    device_id, modelo, telefone = dispositivo_habitual(cur, id_pessoa)
    uf_compra = uf_casa if uf_casa in UF_LEGITIMAS else random.choice(UF_LEGITIMAS)

    if fraude == "geolocalizacao":
        uf_compra = random.choice(UF_SUSPEITAS)
    elif fraude == "troca_dispositivo":
        outros = [m for m in MODELOS_DISPOSITIVO if m != modelo]
        device_id, modelo = novo_dispositivo(cur, random.choice(outros))

    geohash = _geo_da_uf(uf_compra, random)[0]

    cur.execute("SELECT id, valor_unit FROM public.produtos ORDER BY random() LIMIT %s",
                (random.randint(1, 5),))
    itens, total = [], 0
    for id_produto, valor_unit in cur.fetchall():
        qtde = random.randint(1, 4)
        valor_item = round(valor_unit * qtde, 2)
        total += valor_item
        itens.append((id_produto, qtde, valor_item))

    cur.execute("""INSERT INTO public.pedidos (id_pessoa, dt_venda, valor_total, id_endereco_entrega, status)
                   VALUES (%s, now(), %s, %s, 'criado') RETURNING id""",
                (id_pessoa, total, id_endereco))
    id_pedido = cur.fetchone()[0]

    for id_produto, qtde, valor_item in itens:
        cur.execute("""INSERT INTO public.itens_pedidos (id_pedido, id_produto, qtde, valor_total)
                       VALUES (%s, %s, %s, %s)""", (id_pedido, id_produto, qtde, valor_item))

    cur.execute("""INSERT INTO public.auditoria_pedidos
                       (id_pedido, dispositivo, geohash, telefone, device_id, uf, is_fraude)
                   VALUES (%s, %s, %s, %s, %s, %s, false)""",
                (id_pedido, modelo, geohash, telefone, device_id, uf_compra))

    forma, parcelas = ext_mod.sortear_pagamento(fraude is not None, random)
    cur.execute("""INSERT INTO public.pagamentos (id_pedido, forma, parcelas, valor, status)
                   VALUES (%s, %s, %s, %s, 'pendente')""", (id_pedido, forma, parcelas, total))

    cur.execute("""INSERT INTO public.status_pedidos (id_pedido, status, dt_evento)
                   VALUES (%s, 'criado', now())""", (id_pedido,))
    return id_pedido


def processa_pagamentos(cur):
    """Pix e cartao respondem em segundos; boleto leva horas. Devolve (aprovados, recusados)."""
    cur.execute("""
        SELECT g.id, g.id_pedido, g.forma, g.created_at < now() - interval '%s days' AS vencido
        FROM public.pagamentos g
        JOIN public.pedidos p ON p.id = g.id_pedido
        WHERE g.status = 'pendente' AND p.status = 'criado'
          AND (   (g.forma <> 'boleto' AND g.created_at < now() - interval '15 seconds')
               OR (g.forma =  'boleto' AND g.created_at < now() - interval '6 hours'))
        ORDER BY g.created_at LIMIT 15""" % ext_mod.DIAS_VENCIMENTO_BOLETO)
    aprovados = recusados = 0
    for id_pagamento, id_pedido, forma, vencido in cur.fetchall():
        if forma == "boleto" and vencido:
            cur.execute("UPDATE public.pagamentos SET status = 'expirado' WHERE id = %s", (id_pagamento,))
            registrar_status(cur, id_pedido, "cancelado")
            recusados += 1
        elif random.random() < ext_mod.TAXA_PAGAMENTO_RECUSADO:
            cur.execute("UPDATE public.pagamentos SET status = 'recusado', dt_pagamento = now() WHERE id = %s",
                        (id_pagamento,))
            registrar_status(cur, id_pedido, "cancelado")
            recusados += 1
        else:
            cur.execute("UPDATE public.pagamentos SET status = 'aprovado', dt_pagamento = now() WHERE id = %s",
                        (id_pagamento,))
            registrar_status(cur, id_pedido, "pago")
            aprovados += 1
    return aprovados, recusados


def separa_pedidos(cur, maximo):
    """O galpao separa pedidos pagos ha pelo menos 30 minutos."""
    cur.execute("""
        SELECT p.id FROM public.pedidos p
        JOIN public.pagamentos g ON g.id_pedido = p.id AND g.status = 'aprovado'
        WHERE p.status = 'pago' AND g.dt_pagamento < now() - interval '30 minutes'
        ORDER BY g.dt_pagamento LIMIT %s""", (maximo,))
    ids = [r[0] for r in cur.fetchall()]
    for id_pedido in ids:
        registrar_status(cur, id_pedido, "separado")
    return len(ids)


def despacha_transporte(cur):
    """Junta pedidos separados ha mais de 1 hora, da mesma UF, num caminhao.

    Devolve a quantidade de pedidos embarcados (0 se nenhum caminhao saiu).
    """
    cur.execute("""
        SELECT e.uf, array_agg(p.id ORDER BY s.dt_evento)
        FROM public.pedidos p
        JOIN public.status_pedidos s ON s.id_pedido = p.id AND s.status = 'separado'
        JOIN public.enderecos e ON e.id = p.id_endereco_entrega
        WHERE p.status = 'separado' AND s.dt_evento < now() - interval '1 hour'
        GROUP BY e.uf ORDER BY count(*) DESC LIMIT 1""")
    linha = cur.fetchone()
    if not linha:
        return 0
    uf, ids = linha
    ids = ids[:ext_mod.CAPACIDADE_CAMINHAO]
    t = ext_mod.sortear_transportadora(uf, random)

    cur.execute("""
        SELECT COALESCE(sum(i.qtde * COALESCE(pr.peso_gramas, 0)), 0)
        FROM public.itens_pedidos i JOIN public.produtos pr ON pr.id = i.id_produto
        WHERE i.id_pedido = ANY(%s)""", (ids,))
    peso_total = int(cur.fetchone()[0])
    prazo = ext_mod.PRAZO_DIAS.get(uf, 3)

    cur.execute("""
        INSERT INTO public.transportes
            (id_transportadora, placa, peso_total_gramas, valor_frete, dt_saida, dt_entrega_prevista)
        VALUES (%s, %s, %s, %s, now(), now() + %s * interval '1 day') RETURNING id""",
                (t["id"], ext_mod.sortear_placa(random), peso_total,
                 ext_mod.calcular_frete(peso_total, t["custo_por_kg"]), prazo))
    id_transporte = cur.fetchone()[0]
    for id_pedido in ids:
        cur.execute("INSERT INTO public.carga_pedidos (id_transporte, id_pedido) VALUES (%s, %s)",
                    (id_transporte, id_pedido))
        registrar_status(cur, id_pedido, "enviado")
    return len(ids)


def entrega_transporte(cur):
    """Entrega um caminhao que esta na estrada ha mais de 1 dia.

    A transportadora "lenta" so entrega depois do prazo: e ela que o aluno
    vai flagrar no dashboard de logistica. Devolve os pedidos entregues.
    """
    cur.execute("""
        SELECT id FROM public.transportes
        WHERE dt_entrega IS NULL AND dt_saida < now() - interval '1 day'
          AND (id_transportadora <> %s OR dt_entrega_prevista < now())
        ORDER BY dt_saida LIMIT 1""", (ext_mod.ID_TRANSPORTADORA_LENTA,))
    linha = cur.fetchone()
    if not linha:
        return 0
    id_transporte = linha[0]
    cur.execute("UPDATE public.transportes SET dt_entrega = now() WHERE id = %s", (id_transporte,))
    cur.execute("""SELECT c.id_pedido FROM public.carga_pedidos c
                   JOIN public.pedidos p ON p.id = c.id_pedido
                   WHERE c.id_transporte = %s AND p.status = 'enviado'""", (id_transporte,))
    ids = [r[0] for r in cur.fetchall()]
    for id_pedido in ids:
        registrar_status(cur, id_pedido, "entregue")
    return len(ids)


def devolve_pedido(cur):
    """Um cliente devolve um pedido entregue ha mais de 2 dias."""
    cur.execute("""
        SELECT p.id FROM public.pedidos p
        JOIN public.status_pedidos s ON s.id_pedido = p.id AND s.status = 'entregue'
        JOIN public.auditoria_pedidos a ON a.id_pedido = p.id AND NOT a.is_fraude
        WHERE p.status = 'entregue'
          AND s.dt_evento BETWEEN now() - interval '10 days' AND now() - interval '2 days'
        ORDER BY random() LIMIT 1""")
    linha = cur.fetchone()
    if not linha:
        return 0
    registrar_status(cur, linha[0], "devolvido")
    cur.execute("UPDATE public.pagamentos SET status = 'estornado' WHERE id_pedido = %s AND status = 'aprovado'",
                (linha[0],))
    return 1


def confirma_fraude(cur, id_pedido, motivo):
    """O analista antifraude confirma: UPDATE na auditoria (e as consequencias)."""
    cur.execute("""UPDATE public.auditoria_pedidos
                   SET is_fraude = true, motivo_fraude = %s, dt_fraude = now()
                   WHERE id_pedido = %s AND NOT is_fraude""", (motivo, id_pedido))
    if cur.rowcount == 0:
        return 0
    cur.execute("UPDATE public.pagamentos SET status = 'estornado' WHERE id_pedido = %s AND status = 'aprovado'",
                (id_pedido,))
    cur.execute("UPDATE public.pagamentos SET status = 'recusado' WHERE id_pedido = %s AND status = 'pendente'",
                (id_pedido,))
    cur.execute("SELECT status FROM public.pedidos WHERE id = %s", (id_pedido,))
    if cur.fetchone()[0] in ("criado", "pago", "separado"):
        registrar_status(cur, id_pedido, "cancelado")     # descoberta a tempo
    return 1


def suspeitas_pendentes(cur):
    """Compras de fora da area atendida que ainda ninguem analisou."""
    cur.execute("""SELECT id_pedido FROM public.auditoria_pedidos
                   WHERE NOT is_fraude AND uf IS NOT NULL AND uf NOT IN %s""", (tuple(UF_LEGITIMAS),))
    return [r[0] for r in cur.fetchall()]


def muda_endereco(cur, fake):
    """Uma pessoa se muda: o endereco antigo deixa de ser o principal (UPDATE)
    e nasce um novo (INSERT). E isso que alimenta o SCD tipo 2 no DW."""
    cur.execute("""SELECT e.id, e.id_pessoa, e.uf FROM public.enderecos e
                   WHERE e.is_principal ORDER BY random() LIMIT 1""")
    linha = cur.fetchone()
    if not linha:
        return None
    id_endereco, id_pessoa, uf = linha
    if random.random() < 0.3:
        uf = random.choice([x for x in UF_LEGITIMAS if x != uf])
    cur.execute("UPDATE public.enderecos SET is_principal = false WHERE id = %s", (id_endereco,))
    gerar_endereco(cur, fake, id_pessoa, uf)
    return id_pessoa


def reajusta_preco(cur):
    """Um produto muda de preco (UPDATE em produtos)."""
    fator = random.choice([0.92, 0.95, 1.03, 1.05, 1.08])
    cur.execute("""UPDATE public.produtos SET valor_unit = round(valor_unit * %s, 2)
                   WHERE id = (SELECT id FROM public.produtos ORDER BY random() LIMIT 1)
                   RETURNING id""", (fator,))
    return cur.fetchone()[0]


__all__ = [n for n in dir() if not n.startswith("_")] + ["gerar_universo", "datetime", "timedelta"]
