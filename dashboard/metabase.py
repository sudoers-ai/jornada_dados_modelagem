# -*- coding: utf-8 -*-
"""
Conversa com o Metabase pela API. Tres usos:

    python dashboard/metabase.py sync       -> make metabase-sync
        Pede ao Metabase para reler as tabelas dos dois bancos e ESPERA ele
        terminar. Sem isso, tabela e coluna nova nao aparecem na interface.

    python dashboard/metabase.py conferir   -> make conferir-dashboards
        A prova da etapa 8: roda todos os graficos dos dashboards e diz
        quais estao quebrados, quais ainda carregam o erro antigo e quais
        dashboards novos ainda faltam.

    python dashboard/metabase.py gabarito   -> make gabarito-dashboards
        Aplica a resposta pronta: conserta os graficos antigos e cria os
        tres dashboards novos, com os mesmos SQLs de dashboard/cards/.
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "data_simulator"))

V, A, R, C, N, F = "\033[92m", "\033[93m", "\033[91m", "\033[90m", "\033[1m", "\033[0m"

URL = os.getenv("METABASE_URL", "http://metabase:3000").rstrip("/")
USUARIO = "contato@sudoers.com.br"
SENHA = "*liga01"

BANCO_OLTP = "Liga Sudoers"
BANCO_DW = "Liga DW"
PASTA_CARDS = os.path.join(RAIZ, "dashboard", "cards")

# --------------------------------------------------------------------------
# O GABARITO da etapa 8. E a mesma coisa que o dashboard/README.md ensina a
# fazer na mao; os SQLs sao os arquivos de dashboard/cards/.
# --------------------------------------------------------------------------

# Graficos ANTIGOS que precisam de conserto (id e nome vem do backup herdado).
CONSERTOS = [
    {"id": 40, "arquivo": "transacional_01_pedidos_por_data.sql",
     "exige": ["status"], "motivo": "ainda pega os 7 PRIMEIROS dias e conta pedidos cancelados"},
    {"id": 44, "arquivo": "transacional_02_produtos_vendidos.sql",
     "exige": ["valor_total"], "motivo": "ainda soma o preço de catálogo (valor_unit) e ignora a quantidade"},
    {"id": 45, "arquivo": "transacional_03_valor_por_pedido.sql",
     "nome": "Valor por pedido nos últimos 7 dias",
     "proibe": ["valor_unit"], "motivo": "ainda agrupa por produto: o \"ticket médio\" sai errado"},
    {"id": 48, "arquivo": "dw_01_churn.sql",
     "exige": ["is_atual"], "motivo": "ainda agrupa por nome e ignora a versão atual da pessoa (SCD 2)"},
    {"id": 50, "arquivo": "dw_02_crescimento_faturamento.sql",
     "exige": ["valor_total", "is_fraude"], "motivo": "ainda não desconta fraude e cancelamento do faturamento"},
    {"id": 52, "arquivo": "dw_03_ticket_medio_categoria.sql",
     "exige": ["valor_total"], "proibe_regex": r"sk_produto\s*=\s*\w+\.id\b",
     "motivo": "ainda liga a fato na dimensão pelo id em vez da sk_produto"},
    {"id": 54, "arquivo": "dw_04_regioes_faturamento.sql", "opcional": True,
     "exige": ["dim_localidade"], "motivo": "ainda usa o geohash cru em vez da dim_localidade"},
    {"id": 55, "arquivo": "dw_04_regioes_faturamento.sql",
     "viz": {"pie.dimension": ["uf"], "pie.metric": "faturamento"},
     "exige": ["dim_localidade"], "motivo": "ainda descobre a UF por CASE no geohash em vez da dim_localidade"},
]

RENOMEAR_DASHBOARD = {"Datawehoure": "Data Warehouse"}

# Grafico NOVO num dashboard que ja existia
ACRESCIMOS = [
    {"dashboard": "Transacional", "banco": BANCO_OLTP,
     "nome": "Pedidos por situação nos últimos 7 dias", "arquivo": "transacional_04_pedidos_por_situacao.sql",
     "display": "bar", "viz": {"graph.dimensions": ["situacao"], "graph.metrics": ["pedidos"]},
     "tamanho": (24, 7)},
]

# Dashboards NOVOS (todos sobre o DW). tamanho = (largura, altura) numa grade de 24 colunas.
DASHBOARDS_NOVOS = [
    {"nome": "Antifraude", "descricao": "Demanda 1: onde, como e por quanto a fraude acontece.", "cards": [
        {"nome": "Taxa de fraude (%)", "arquivo": "antifraude_01_taxa_fraude.sql",
         "display": "scalar", "viz": {}, "tamanho": (6, 8)},
        {"nome": "Fraudes por motivo", "arquivo": "antifraude_02_fraudes_por_motivo.sql",
         "display": "pie", "viz": {"pie.dimension": ["motivo"], "pie.metric": "pedidos"}, "tamanho": (9, 8)},
        {"nome": "Valor das fraudes: barradas x descobertas tarde", "arquivo": "antifraude_05_desfecho.sql",
         "display": "pie", "viz": {"pie.dimension": ["desfecho"], "pie.metric": "valor"}, "tamanho": (9, 8)},
        {"nome": "Pedidos de fora da área atendida, por UF", "arquivo": "antifraude_03_fora_da_area.sql",
         "display": "bar", "viz": {"graph.dimensions": ["uf"], "graph.metrics": ["pedidos"]}, "tamanho": (12, 7)},
        {"nome": "Taxa de fraude por forma de pagamento (%)", "arquivo": "antifraude_06_fraude_por_pagamento.sql",
         "display": "bar", "viz": {"graph.dimensions": ["forma_pagamento"], "graph.metrics": ["taxa_fraude_pct"]},
         "tamanho": (12, 7)},
        {"nome": "Aparelhos compartilhados (suspeita de anel de fraude)",
         "arquivo": "antifraude_04_aparelhos_compartilhados.sql",
         "display": "table", "viz": {}, "tamanho": (24, 7)},
    ]},
    {"nome": "Logística", "descricao": "Demanda 2: peso transportado, custo de frete e pontualidade.", "cards": [
        {"nome": "Pedidos em trânsito agora", "arquivo": "logistica_05_em_transito.sql",
         "display": "scalar", "viz": {}, "tamanho": (6, 7)},
        {"nome": "Peso médio por pedido, por dia (kg)", "arquivo": "logistica_01_peso_medio_diario.sql",
         "display": "line", "viz": {"graph.dimensions": ["data"], "graph.metrics": ["peso_medio_kg"]},
         "tamanho": (18, 7)},
        {"nome": "Entregas atrasadas por transportadora (%)", "arquivo": "logistica_03_atraso_por_transportadora.sql",
         "display": "bar", "viz": {"graph.dimensions": ["transportadora"], "graph.metrics": ["pct_atrasadas"]},
         "tamanho": (12, 7)},
        {"nome": "Frete pago por mês, por transportadora", "arquivo": "logistica_04_frete_por_mes.sql",
         "display": "bar",
         "viz": {"graph.dimensions": ["mes", "transportadora"], "graph.metrics": ["frete"],
                 "stackable.stack_type": "stacked"}, "tamanho": (12, 7)},
        {"nome": "Custo e pontualidade por transportadora", "arquivo": "logistica_02_custo_e_pontualidade.sql",
         "display": "table", "viz": {}, "tamanho": (24, 7)},
    ]},
    {"nome": "Ciclo do pedido", "descricao": "Demanda 3: por onde o pedido passa e onde ele demora.", "cards": [
        {"nome": "Funil do pedido", "arquivo": "ciclo_01_funil.sql",
         "display": "funnel", "viz": {"funnel.dimension": "etapa", "funnel.metric": "pedidos"}, "tamanho": (12, 8)},
        {"nome": "Tempo médio de cada etapa (horas)", "arquivo": "ciclo_02_tempo_por_etapa.sql",
         "display": "bar", "viz": {"graph.dimensions": ["etapa"], "graph.metrics": ["horas"]}, "tamanho": (12, 8)},
        {"nome": "Pedidos em aberto, por situação", "arquivo": "ciclo_03_pedidos_em_aberto.sql",
         "display": "bar", "viz": {"graph.dimensions": ["situacao"], "graph.metrics": ["pedidos"]}, "tamanho": (8, 7)},
        {"nome": "Dias até a entrega, por semana da compra", "arquivo": "ciclo_04_dias_ate_entrega.sql",
         "display": "line", "viz": {"graph.dimensions": ["semana"], "graph.metrics": ["dias_ate_entrega"]},
         "tamanho": (8, 7)},
        {"nome": "Pedidos por dia da semana", "arquivo": "ciclo_05_pedidos_por_dia_da_semana.sql",
         "display": "bar", "viz": {"graph.dimensions": ["nome_dia"], "graph.metrics": ["pedidos"]}, "tamanho": (8, 7)},
    ]},
]


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
class ErroMetabase(Exception):
    pass


def api(metodo, caminho, corpo=None, sessao=None, limite=120):
    dados = None if corpo is None else json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(URL + caminho, data=dados, method=metodo)
    req.add_header("Content-Type", "application/json")
    if sessao:
        req.add_header("X-Metabase-Session", sessao)
    try:
        with urllib.request.urlopen(req, timeout=limite) as resp:
            texto = resp.read().decode("utf-8")
            return json.loads(texto) if texto.strip() else None
    except urllib.error.HTTPError as e:
        raise ErroMetabase("%s %s -> HTTP %d: %s" % (metodo, caminho, e.code, e.read().decode("utf-8")[:300]))


def entrar():
    """Espera o Metabase responder e faz login."""
    inicio = time.time()
    avisou = False
    while True:
        try:
            if api("GET", "/api/health", limite=5).get("status") == "ok":
                break
        except Exception:               # noqa: BLE001
            pass
        if time.time() - inicio > 240:
            print("%s❌ O Metabase não respondeu em %s.%s" % (R, URL, F))
            print("   Ele está no ar? Rode: make status   (ele leva 1 a 2 minutos para abrir)")
            sys.exit(1)
        if not avisou:
            print("  %s⏳ esperando o Metabase abrir...%s" % (A, F), flush=True)
            avisou = True
        time.sleep(3)
    try:
        return api("POST", "/api/session", {"username": USUARIO, "password": SENHA})["id"]
    except ErroMetabase as e:
        print("%s❌ Não consegui entrar no Metabase com o usuário padrão.%s\n   %s" % (R, F, e))
        print("   Se você trocou a senha de %s, este comando não funciona." % USUARIO)
        sys.exit(1)


def bancos(sessao):
    return {b["name"]: b["id"] for b in api("GET", "/api/database", sessao=sessao)["data"]}


def simples(texto):
    """minusculas e sem acento: 'Logística' == 'logistica'."""
    sem = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem).strip().lower()


def ler_sql(arquivo):
    with open(os.path.join(PASTA_CARDS, arquivo), encoding="utf-8") as fh:
        return fh.read().strip()


def rodar_card(sessao, id_card):
    """Devolve (linhas, erro)."""
    try:
        r = api("POST", "/api/card/%d/query" % id_card, sessao=sessao)
    except ErroMetabase as e:
        return 0, str(e)
    if r.get("error"):
        return 0, str(r["error"]).strip().splitlines()[0]
    return len(r.get("data", {}).get("rows", [])), None


# --------------------------------------------------------------------------
# sync
# --------------------------------------------------------------------------
def tabelas_reais(banco):
    import psycopg2
    from verificador import config_conexao
    conn = psycopg2.connect(**config_conexao(banco))
    cur = conn.cursor()
    cur.execute("""SELECT table_name, column_name FROM information_schema.columns
                   WHERE table_schema = 'public'""")
    real = {}
    for t, c in cur.fetchall():
        real.setdefault(t, set()).add(c)
    conn.close()
    return real


def tabelas_no_metabase(sessao, id_banco):
    meta = api("GET", "/api/database/%d/metadata" % id_banco, sessao=sessao)
    return {t["name"]: {f["name"] for f in t.get("fields", [])}
            for t in meta.get("tables", []) if t.get("schema") == "public"}


def cmd_sync():
    sessao = entrar()
    ids = bancos(sessao)
    tudo_certo = True
    for nome, chave in ((BANCO_OLTP, "oltp"), (BANCO_DW, "dw")):
        real = tabelas_reais(chave)
        api("POST", "/api/database/%d/sync_schema" % ids[nome], sessao=sessao)
        inicio = time.time()
        while True:
            visto = tabelas_no_metabase(sessao, ids[nome])
            if visto == real:
                print("  %s✅%s %-13s %d tabelas sincronizadas" % (V, F, nome + ":", len(real)))
                break
            if time.time() - inicio > 120:
                faltando = sorted(set(real) - set(visto))
                print("  %s❌%s %s: o Metabase não terminou de sincronizar em 2 minutos." % (R, F, nome))
                if faltando:
                    print("     ainda não enxerga: %s" % ", ".join(faltando))
                tudo_certo = False
                break
            time.sleep(2)
    if tudo_certo:
        print("  O Metabase já enxerga as tabelas e colunas novas.")
    return 0 if tudo_certo else 1


# --------------------------------------------------------------------------
# conferir
# --------------------------------------------------------------------------
def cmd_conferir():
    sessao = entrar()
    pend, avisos, ok = [], [], 0

    dashboards = [d for d in api("GET", "/api/dashboard", sessao=sessao) if not d.get("archived")]
    por_nome = {simples(d["name"]): d for d in dashboards}

    quebrados = set()

    # 1) todo grafico de todo dashboard roda sem erro
    for d in sorted(dashboards, key=lambda x: x["name"]):
        completo = api("GET", "/api/dashboard/%d" % d["id"], sessao=sessao)
        cards = [dc["card"] for dc in completo.get("dashcards", []) if dc.get("card")]
        print()
        print("%s%s%s  %s(%d gráficos)%s" % (N, d["name"], F, C, len(cards), F))
        for card in cards:
            linhas, erro = rodar_card(sessao, card["id"])
            if erro:
                quebrados.add(card["id"])
                pend.append((d["name"], card["name"], "está quebrado: %s" % erro[:110]))
                print("  %s❌%s %s" % (R, F, card["name"]))
            else:
                ok += 1
                print("  %s✅%s %s %s(%d linhas)%s" % (V, F, card["name"], C, linhas, F))

    # 2) os graficos antigos ainda carregam o erro antigo?
    for c in CONSERTOS:
        try:
            card = api("GET", "/api/card/%d" % c["id"], sessao=sessao)
        except ErroMetabase:
            continue                     # o aluno apagou ou recriou: tudo bem
        if card.get("archived") or c["id"] in quebrados:
            continue                     # quebrado ja foi apontado acima
        sql = (card.get("dataset_query", {}).get("native", {}) or {}).get("query", "") or ""
        sql_min = sql.lower()
        errado = any(t.lower() not in sql_min for t in c.get("exige", []))
        errado = errado or any(t.lower() in sql_min for t in c.get("proibe", []))
        if c.get("proibe_regex") and re.search(c["proibe_regex"], sql, re.I):
            errado = True
        if errado:
            alvo = avisos if c.get("opcional") else pend
            alvo.append(("gráfico antigo", card["name"], c["motivo"]))

    # 3) o nome com erro de digitacao
    for errado, certo in RENOMEAR_DASHBOARD.items():
        if simples(errado) in por_nome:
            pend.append(("dashboard", errado, "renomeie para \"%s\"" % certo))

    # 4) os dashboards novos existem, com graficos suficientes?
    for esperado in DASHBOARDS_NOVOS:
        d = por_nome.get(simples(esperado["nome"]))
        if not d:
            pend.append(("dashboard", esperado["nome"], "ainda não foi criado"))
            continue
        completo = api("GET", "/api/dashboard/%d" % d["id"], sessao=sessao)
        n = len([dc for dc in completo.get("dashcards", []) if dc.get("card")])
        if n < len(esperado["cards"]):
            pend.append(("dashboard", esperado["nome"],
                         "tem %d gráfico(s); o roteiro pede %d" % (n, len(esperado["cards"]))))
    for a in ACRESCIMOS:
        d = por_nome.get(simples(a["dashboard"]))
        if d:
            completo = api("GET", "/api/dashboard/%d" % d["id"], sessao=sessao)
            nomes = {simples(dc["card"]["name"]) for dc in completo.get("dashcards", []) if dc.get("card")}
            if simples(a["nome"]) not in nomes:
                pend.append(("dashboard", a["dashboard"], "falta o gráfico novo \"%s\"" % a["nome"]))

    print()
    if pend:
        print("%s❌ Dashboards incompletos.%s O que falta:" % (R, F))
        print()
        for onde, nome, problema in pend:
            print("   %s• %s%s" % (N, nome, F))
            print("       %s" % problema)
        print()
        print("   %d pendência(s). Passo a passo: dashboard/README.md" % len(pend))
        print("   %sTravou? `make gabarito-dashboards` aplica a resposta pronta.%s" % (C, F))
    else:
        print("%s✅ Dashboards conferidos:%s %d gráficos rodando, antigos consertados, %d dashboards novos no ar."
              % (V, F, ok, len(DASHBOARDS_NOVOS)))
    for onde, nome, problema in avisos:
        print("   %s⚠️  %s%s" % (A, nome, F))
        print("       %s%s (este não está em nenhum dashboard: não impede de seguir)%s" % (A, problema, F))
    print()
    return 1 if pend else 0


# --------------------------------------------------------------------------
# gabarito
# --------------------------------------------------------------------------
def consulta_nativa(id_banco, sql):
    return {"type": "native", "database": id_banco, "native": {"query": sql, "template-tags": {}}}


def garantir_card(sessao, existentes, id_banco, spec):
    corpo = {
        "name": spec["nome"], "display": spec["display"],
        "dataset_query": consulta_nativa(id_banco, ler_sql(spec["arquivo"])),
        "visualization_settings": spec.get("viz", {}), "collection_id": None,
    }
    atual = existentes.get(simples(spec["nome"]))
    if atual:
        api("PUT", "/api/card/%d" % atual["id"], corpo, sessao=sessao)
        return atual["id"]
    return api("POST", "/api/card", corpo, sessao=sessao)["id"]


def montar_grade(ids_e_tamanhos, linha_inicial=0, primeiro_id=-1):
    """Distribui os graficos da esquerda para a direita numa grade de 24 colunas."""
    dashcards, col, linha, altura_da_linha, n = [], 0, linha_inicial, 0, primeiro_id
    for id_card, (largura, altura) in ids_e_tamanhos:
        if col + largura > 24:
            col, linha, altura_da_linha = 0, linha + altura_da_linha, 0
        dashcards.append({"id": n, "card_id": id_card, "row": linha, "col": col,
                          "size_x": largura, "size_y": altura,
                          "parameter_mappings": [], "visualization_settings": {}})
        col += largura
        altura_da_linha = max(altura_da_linha, altura)
        n -= 1
    return dashcards


def cmd_gabarito():
    sessao = entrar()
    ids = bancos(sessao)
    print("Aplicando o gabarito dos dashboards...")
    cmd_sync_silencioso(sessao, ids)

    # 1) consertos
    for c in CONSERTOS:
        try:
            card = api("GET", "/api/card/%d" % c["id"], sessao=sessao)
        except ErroMetabase:
            continue
        corpo = {"dataset_query": consulta_nativa(card["database_id"], ler_sql(c["arquivo"]))}
        if c.get("nome"):
            corpo["name"] = c["nome"]
        if c.get("viz"):
            corpo["visualization_settings"] = c["viz"]
        api("PUT", "/api/card/%d" % c["id"], corpo, sessao=sessao)
        print("  %s✅%s consertado: %s" % (V, F, c.get("nome") or card["name"]))

    dashboards = {simples(d["name"]): d for d in api("GET", "/api/dashboard", sessao=sessao)
                  if not d.get("archived")}

    # 2) nome com erro de digitacao
    for errado, certo in RENOMEAR_DASHBOARD.items():
        d = dashboards.pop(simples(errado), None)
        if d:
            api("PUT", "/api/dashboard/%d" % d["id"], {"name": certo}, sessao=sessao)
            dashboards[simples(certo)] = d
            print("  %s✅%s dashboard renomeado: %s -> %s" % (V, F, errado, certo))

    existentes = {simples(c["name"]): c for c in api("GET", "/api/card", sessao=sessao)
                  if not c.get("archived")}

    # 3) grafico novo em dashboard antigo
    for a in ACRESCIMOS:
        d = dashboards.get(simples(a["dashboard"]))
        if not d:
            continue
        id_card = garantir_card(sessao, existentes, ids[a["banco"]], a)
        completo = api("GET", "/api/dashboard/%d" % d["id"], sessao=sessao)
        atuais = completo.get("dashcards", [])
        if id_card not in [dc.get("card_id") for dc in atuais]:
            fim = max([dc["row"] + dc["size_y"] for dc in atuais] or [0])
            mantidos = [{k: dc[k] for k in ("id", "card_id", "row", "col", "size_x", "size_y",
                                            "parameter_mappings", "visualization_settings")}
                        for dc in atuais]
            api("PUT", "/api/dashboard/%d" % d["id"],
                {"dashcards": mantidos + montar_grade([(id_card, a["tamanho"])], fim)}, sessao=sessao)
        print("  %s✅%s gráfico novo em %s: %s" % (V, F, a["dashboard"], a["nome"]))

    # 4) dashboards novos
    for esperado in DASHBOARDS_NOVOS:
        d = dashboards.get(simples(esperado["nome"]))
        if not d:
            d = api("POST", "/api/dashboard",
                    {"name": esperado["nome"], "description": esperado["descricao"],
                     "collection_id": None}, sessao=sessao)
        pares = [(garantir_card(sessao, existentes, ids[BANCO_DW], c), c["tamanho"])
                 for c in esperado["cards"]]
        api("PUT", "/api/dashboard/%d" % d["id"], {"dashcards": montar_grade(pares)}, sessao=sessao)
        print("  %s✅%s dashboard %s: %d gráficos" % (V, F, esperado["nome"], len(pares)))

    print()
    return cmd_conferir()


def cmd_sync_silencioso(sessao, ids):
    for nome, chave in ((BANCO_OLTP, "oltp"), (BANCO_DW, "dw")):
        real = tabelas_reais(chave)
        api("POST", "/api/database/%d/sync_schema" % ids[nome], sessao=sessao)
        inicio = time.time()
        while tabelas_no_metabase(sessao, ids[nome]) != real and time.time() - inicio < 120:
            time.sleep(2)


def main():
    comandos = {"sync": cmd_sync, "conferir": cmd_conferir, "gabarito": cmd_gabarito}
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    if comando not in comandos:
        print("uso: python dashboard/metabase.py [sync|conferir|gabarito]")
        return 2
    try:
        return comandos[comando]()
    except ErroMetabase as e:
        print("%s❌ O Metabase recusou um pedido:%s %s" % (R, F, e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
