# -*- coding: utf-8 -*-
"""
Conferencia da modelagem: compara o SEU banco com o DBML do repositorio.

E o "portao" da disciplina. O historico, o streaming e o ETL chamam esta
conferencia ANTES de gravar qualquer coisa. Se o banco nao estiver igual ao
modelo, eles param e dizem exatamente o que falta - tabela por tabela,
coluna por coluna.

Uso direto:
    python data_simulator/verificador.py oltp     # confere o transacional
    python data_simulator/verificador.py dw       # confere o dimensional

O que e conferido:
    - toda tabela do DBML existe
    - toda coluna existe, com a familia de tipo certa e o NOT NULL certo
    - colunas com `default` ou `increment` tem valor padrao no banco
    - chave primaria (simples ou composta)
    - chaves unicas (simples ou compostas)
    - chaves estrangeiras (Ref do DBML)
    - colunas que SOBRARAM no banco e nao existem no modelo
    - toda tabela com `updated_at` tem trigger de UPDATE (so no OLTP)
"""
import os
import re
import sys

V, A, R, C, N, F = "\033[92m", "\033[93m", "\033[91m", "\033[90m", "\033[1m", "\033[0m"

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BANCOS = {
    "oltp": {
        "titulo": "TRANSACIONAL (OLTP)",
        "dbml": os.path.join(RAIZ, "modelagem", "dbml", "02_oltp_evoluido.dbml"),
        "host": os.getenv("OLTP_HOST", "postgres_oltp"),
        "dbname": "liga_sudoers",
        "exige_trigger": True,
        "guia": "modelagem/03_evolucao_oltp/README.md",
        "gabarito": "make gabarito-oltp",
    },
    "dw": {
        "titulo": "DIMENSIONAL (DW)",
        "dbml": os.path.join(RAIZ, "modelagem", "dbml", "04_dw_evoluido.dbml"),
        "host": os.getenv("DW_HOST", "postgres_dw"),
        "dbname": "liga_sudoers_dw",
        "exige_trigger": False,
        "guia": "modelagem/05_evolucao_dw/README.md",
        "gabarito": "make gabarito-dw",
    },
}


def config_conexao(banco):
    """Parametros de conexao (os mesmos do docker-compose.yml)."""
    b = BANCOS[banco]
    return {
        "host": b["host"],
        "port": int(os.getenv("PGPORT_INTERNA", "5432")),
        "dbname": b["dbname"],
        "user": "sudoers",
        "password": "password",
        "connect_timeout": 10,
    }


# --------------------------------------------------------------------------
# 1) Leitor de DBML (so o subconjunto que os arquivos deste repo usam)
# --------------------------------------------------------------------------
def _partes(texto):
    """Quebra 'a, b: `x, y`, c' em pedacos, respeitando aspas e crases."""
    partes, atual, aspas = [], "", None
    for ch in texto:
        if aspas:
            atual += ch
            if ch == aspas:
                aspas = None
        elif ch in "'`\"":
            aspas = ch
            atual += ch
        elif ch == ",":
            partes.append(atual.strip())
            atual = ""
        else:
            atual += ch
    if atual.strip():
        partes.append(atual.strip())
    return partes


def ler_dbml(caminho):
    """Devolve {tabela: {...}} e a lista de referencias (FKs)."""
    tabelas, refs = {}, []
    tabela = None
    em_indices = False

    with open(caminho, encoding="utf-8") as fh:
        linhas = fh.read().splitlines()

    for bruta in linhas:
        linha = bruta.split("//")[0].strip()
        if not linha:
            continue

        m = re.match(r"^Table\s+(\w+)(\s*\[[^\]]*\])?\s*\{$", linha)
        if m:
            tabela = {"colunas": {}, "pk": [], "unicas": []}
            tabelas[m.group(1)] = tabela
            em_indices = False
            continue

        m = re.match(r"^Ref\s*:\s*(\w+)\.(\w+)\s*([<>-])\s*(\w+)\.(\w+)$", linha)
        if m and tabela is None:
            t1, c1, op, t2, c2 = m.groups()
            if op == "<":                      # lado "um" a esquerda: inverte
                t1, c1, t2, c2 = t2, c2, t1, c1
            refs.append((t1, c1, t2, c2))
            continue

        if tabela is None:
            continue

        if linha.startswith("indexes"):
            em_indices = True
            continue
        if linha == "}":
            if em_indices:
                em_indices = False
            else:
                tabela = None
            continue

        if em_indices:
            m = re.match(r"^\(?([\w\s,]+)\)?\s*\[([^\]]*)\]$", linha)
            if m:
                cols = [c.strip() for c in m.group(1).split(",")]
                ajustes = [a.strip().lower() for a in m.group(2).split(",")]
                if "pk" in ajustes:
                    tabela["pk"] = cols
                elif "unique" in ajustes:
                    tabela["unicas"].append(cols)
            continue

        if linha.lower().startswith("note"):
            continue

        m = re.match(r"^(\w+)\s+([\w]+(?:\([\d,\s]+\))?)\s*(?:\[(.*)\])?$", linha)
        if not m:
            raise ValueError("Linha de DBML que nao entendi em %s: %r" % (caminho, bruta))
        nome, tipo, ajustes = m.group(1), m.group(2), m.group(3) or ""
        col = {"tipo": tipo, "not_null": False, "default": False}
        for a in _partes(ajustes):
            al = a.lower()
            if al in ("pk", "primary key"):
                tabela["pk"] = tabela["pk"] + [nome]
                col["not_null"] = True
            elif al == "not null":
                col["not_null"] = True
            elif al == "unique":
                tabela["unicas"].append([nome])
            elif al == "increment":
                col["default"] = True
            elif al.startswith("default"):
                col["default"] = True
        tabela["colunas"][nome] = col

    return tabelas, refs


# --------------------------------------------------------------------------
# 2) Familias de tipo: o modelo diz `varchar`, o Postgres responde
#    `character varying`. O que importa e a familia bater.
# --------------------------------------------------------------------------
def familia_dbml(tipo):
    t = tipo.lower().split("(")[0]
    if t in ("varchar", "char", "text", "character"):
        return "texto"
    if t in ("int", "integer", "serial", "int4"):
        return "inteiro"
    if t in ("bigint", "bigserial", "int8"):
        return "inteiro grande (bigint)"
    if t in ("smallint", "int2"):
        return "inteiro pequeno (smallint)"
    if t in ("numeric", "decimal"):
        return "decimal (numeric)"
    if t in ("timestamp", "datetime"):
        return "timestamp"
    if t == "date":
        return "data (date)"
    if t in ("boolean", "bool"):
        return "booleano"
    return t


def familia_pg(data_type):
    t = data_type.lower()
    if t in ("character varying", "character", "text"):
        return "texto"
    if t == "integer":
        return "inteiro"
    if t == "bigint":
        return "inteiro grande (bigint)"
    if t == "smallint":
        return "inteiro pequeno (smallint)"
    if t == "numeric":
        return "decimal (numeric)"
    if t.startswith("timestamp"):
        return "timestamp"
    if t == "date":
        return "data (date)"
    if t == "boolean":
        return "booleano"
    return t


# --------------------------------------------------------------------------
# 3) Retrato do banco
# --------------------------------------------------------------------------
def retrato_do_banco(cur):
    cur.execute("""
        SELECT table_name, column_name, data_type, is_nullable,
               column_default IS NOT NULL OR is_identity = 'YES' AS tem_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position""")
    colunas = {}
    for t, c, tipo, nulo, tem_default in cur.fetchall():
        colunas.setdefault(t, {})[c] = {
            "tipo": tipo, "not_null": nulo == "NO", "default": bool(tem_default)}

    cur.execute("""
        SELECT rel.relname, con.contype,
               ARRAY(SELECT a.attname FROM unnest(con.conkey) WITH ORDINALITY k(attnum, ord)
                     JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
                     ORDER BY k.ord),
               frel.relname,
               ARRAY(SELECT a.attname FROM unnest(con.confkey) WITH ORDINALITY k(attnum, ord)
                     JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = k.attnum
                     ORDER BY k.ord)
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace ns ON ns.oid = rel.relnamespace
        LEFT JOIN pg_class frel ON frel.oid = con.confrelid
        WHERE ns.nspname = 'public' AND con.contype IN ('p', 'u', 'f')""")
    pks, unicas, fks = {}, {}, set()
    for t, tipo, cols, t_ref, cols_ref in cur.fetchall():
        if tipo == "p":
            pks[t] = list(cols)
        elif tipo == "u":
            unicas.setdefault(t, []).append(sorted(cols))
        elif tipo == "f" and len(cols) == 1:
            fks.add((t, cols[0], t_ref, cols_ref[0]))

    # indice UNIQUE criado com CREATE UNIQUE INDEX tambem vale como chave unica
    cur.execute("""
        SELECT t.relname,
               ARRAY(SELECT a.attname FROM unnest(ix.indkey) WITH ORDINALITY k(attnum, ord)
                     JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
                     ORDER BY k.ord)
        FROM pg_index ix
        JOIN pg_class t ON t.oid = ix.indrelid
        JOIN pg_namespace ns ON ns.oid = t.relnamespace
        WHERE ns.nspname = 'public' AND ix.indisunique AND NOT ix.indisprimary""")
    for t, cols in cur.fetchall():
        unicas.setdefault(t, []).append(sorted(cols))

    cur.execute("""
        SELECT DISTINCT c.relname
        FROM pg_trigger tg
        JOIN pg_class c ON c.oid = tg.tgrelid
        JOIN pg_namespace ns ON ns.oid = c.relnamespace
        WHERE ns.nspname = 'public' AND NOT tg.tgisinternal
          AND (tg.tgtype & 2) = 2      -- BEFORE
          AND (tg.tgtype & 16) = 16    -- UPDATE""")
    com_trigger = {r[0] for r in cur.fetchall()}

    return colunas, pks, unicas, fks, com_trigger


# --------------------------------------------------------------------------
# 4) A conferencia
# --------------------------------------------------------------------------
def conferir(cur, banco):
    """Devolve (pendencias, avisos, resumo). Pendencia impede de seguir."""
    b = BANCOS[banco]
    modelo, refs = ler_dbml(b["dbml"])
    colunas, pks, unicas, fks, com_trigger = retrato_do_banco(cur)

    pend, avisos = [], []

    for tabela, m in modelo.items():
        if tabela not in colunas:
            pend.append((tabela, "a tabela não existe"))
            continue
        banco_cols = colunas[tabela]

        for nome, col in m["colunas"].items():
            alvo = "%s.%s" % (tabela, nome)
            if nome not in banco_cols:
                pend.append((alvo, "a coluna não existe"))
                continue
            real = banco_cols[nome]
            esperado, achado = familia_dbml(col["tipo"]), familia_pg(real["tipo"])
            if esperado != achado:
                pend.append((alvo, "tipo esperado %s, encontrado %s" % (esperado, achado)))
            if col["not_null"] and not real["not_null"]:
                pend.append((alvo, "deveria ser NOT NULL"))
            if not col["not_null"] and real["not_null"]:
                pend.append((alvo, "não deveria ser NOT NULL (o modelo permite nulo)"))
            if col["default"] and not real["default"]:
                pend.append((alvo, "falta o valor padrão (DEFAULT)"))

        for nome in banco_cols:
            if nome not in m["colunas"]:
                pend.append(("%s.%s" % (tabela, nome),
                             "esta coluna não existe no modelo novo (remova com DROP COLUMN)"))

        if m["pk"] and sorted(pks.get(tabela, [])) != sorted(m["pk"]):
            pend.append((tabela, "chave primária deveria ser (%s)" % ", ".join(m["pk"])))

        for cols in m["unicas"]:
            if sorted(cols) not in unicas.get(tabela, []):
                pend.append((tabela, "falta a chave única (UNIQUE) em (%s)" % ", ".join(cols)))

        if b["exige_trigger"] and "updated_at" in m["colunas"] and tabela not in com_trigger:
            pend.append((tabela, "falta o trigger que atualiza o updated_at a cada UPDATE"))

    for t1, c1, t2, c2 in refs:
        if t1 in colunas and c1 in colunas[t1] and (t1, c1, t2, c2) not in fks:
            pend.append(("%s.%s" % (t1, c1),
                         "falta a chave estrangeira (FK) para %s(%s)" % (t2, c2)))

    for tabela in sorted(colunas):
        if tabela not in modelo:
            avisos.append((tabela, "tabela que não está no modelo novo"))

    resumo = {
        "tabelas": len(modelo),
        "colunas": sum(len(m["colunas"]) for m in modelo.values()),
        "fks": len(refs),
    }
    return pend, avisos, resumo


def imprimir_relatorio(banco, pend, avisos, resumo):
    b = BANCOS[banco]
    rel_dbml = os.path.relpath(b["dbml"], RAIZ)
    if pend:
        print()
        print("%s❌ Modelagem do %s incompleta.%s Corrija antes de continuar:" % (R, b["titulo"], F))
        print()
        largura = max(len(a) for a, _ in pend)
        for alvo, problema in pend:
            print("   %s%-*s%s  %s" % (N, largura, alvo, F, problema))
        print()
        print("   %d pendência(s). O modelo de referência é %s%s%s" % (len(pend), N, rel_dbml, F))
        print("   Passo a passo: %s" % b["guia"])
        print("   %sTravou? `%s` aplica a resposta pronta.%s" % (C, b["gabarito"], F))
        print()
    else:
        print("%s✅ Modelagem do %s conferida:%s %d tabelas, %d colunas, %d FKs, 0 pendências."
              % (V, b["titulo"], F, resumo["tabelas"], resumo["colunas"], resumo["fks"]))
    for alvo, problema in avisos:
        print("   %s⚠️  %s: %s (não impede de seguir)%s" % (A, alvo, problema, F))


def exigir_modelagem(conn, banco):
    """Confere e ENCERRA o programa com erro se houver pendencia."""
    cur = conn.cursor()
    pend, avisos, resumo = conferir(cur, banco)
    cur.close()
    imprimir_relatorio(banco, pend, avisos, resumo)
    if pend:
        sys.exit(1)


def main():
    banco = sys.argv[1] if len(sys.argv) > 1 else ""
    if banco not in BANCOS:
        print("uso: python data_simulator/verificador.py [oltp|dw]")
        return 2
    import psycopg2
    try:
        conn = psycopg2.connect(**config_conexao(banco))
    except psycopg2.OperationalError as e:
        print("%s❌ Não consegui conectar no banco %s.%s\n   %s" % (R, BANCOS[banco]["titulo"], F, str(e).strip()))
        print("   Os containers estão no ar? Rode: make subir")
        return 1
    exigir_modelagem(conn, banco)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
