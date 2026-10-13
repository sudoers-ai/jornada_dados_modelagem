# -*- coding: utf-8 -*-
"""
Confere se a documentacao e os arquivos de resposta dizem a MESMA coisa.

Ferramenta de quem MANTEM o repositorio. Roda sem banco e sem Docker:

    python3 tests/conferir_docs.py

O que e conferido:
  1. todo SQL de DDL mostrado nos roteiros das etapas 3 e 6 existe, igual,
     no gabarito correspondente (modelagem/ddl/gabarito/);
  2. todo SQL de grafico mostrado no roteiro da etapa 8 e identico a um
     arquivo de dashboard/cards/, e todo arquivo de la aparece no roteiro;
  3. todo link relativo e toda imagem citada nos .md existe no repositorio.
"""
import os
import re
import sys
from urllib.parse import unquote

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V, R, F = "\033[92m", "\033[91m", "\033[0m"
erros = []


def ler(caminho):
    with open(os.path.join(RAIZ, caminho), encoding="utf-8") as fh:
        return fh.read()


def normalizar(sql):
    sql = re.sub(r"--[^\n]*", "", sql)
    return re.sub(r"\s+", " ", sql).strip().lower()


def blocos(md, tipo):
    padrao = r"<!--\s*rodar:\s*%s[^>]*-->\s*\n```sql\n(.*?)\n```" % tipo
    return re.findall(padrao, md, re.S)


def conferir_gabarito(readme, tipo, gabarito):
    alvo = normalizar(ler(gabarito))
    n = 0
    for bloco in blocos(ler(readme), tipo):
        for comando in bloco.split(";"):
            c = normalizar(comando)
            # so DDL: consultas e comandos do psql (\dt) nao vao para o gabarito
            if not c or not re.match(r"(create|alter|drop|truncate)\b", c):
                continue
            n += 1
            if c not in alvo:
                erros.append("%s: comando que nao esta em %s:\n      %s" % (readme, gabarito, c[:110]))
    return n


def conferir_cards():
    pasta = os.path.join(RAIZ, "dashboard", "cards")
    arquivos = {a: normalizar(ler(os.path.join("dashboard", "cards", a))) for a in sorted(os.listdir(pasta))}
    md = ler("dashboard/README.md")
    no_readme = [normalizar(b) for tipo in ("oltp", "dw") for b in blocos(md, tipo)]
    for b in no_readme:
        if b not in arquivos.values():
            erros.append("dashboard/README.md: SQL que nao e igual a nenhum arquivo de dashboard/cards/:\n      %s" % b[:110])
    for nome, sql in arquivos.items():
        if sql not in no_readme:
            erros.append("dashboard/cards/%s nao aparece (igual) no dashboard/README.md" % nome)
    return len(no_readme)


def conferir_links():
    n = 0
    for pasta, _, nomes in os.walk(RAIZ):
        if ".git" in pasta.split(os.sep) or "entregas" in pasta.split(os.sep):
            continue
        for nome in nomes:
            if not nome.endswith(".md"):
                continue
            caminho = os.path.join(pasta, nome)
            texto = open(caminho, encoding="utf-8").read()
            texto = re.sub(r"```.*?```", "", texto, flags=re.S)      # ignora blocos de codigo
            for alvo in re.findall(r"\]\(([^)\s]+)", texto):
                if re.match(r"(https?:|mailto:|#)", alvo):
                    continue
                arquivo = unquote(alvo.split("#")[0])
                if not arquivo:
                    continue
                n += 1
                if not os.path.exists(os.path.normpath(os.path.join(pasta, arquivo))):
                    erros.append("%s: link quebrado -> %s" % (os.path.relpath(caminho, RAIZ), alvo))
    return n


def main():
    a = conferir_gabarito("modelagem/03_evolucao_oltp/README.md", "oltp", "modelagem/ddl/gabarito/oltp_evolucao.sql")
    b = conferir_gabarito("modelagem/05_evolucao_dw/README.md", "dw", "modelagem/ddl/gabarito/dw_evolucao.sql")
    c = conferir_cards()
    d = conferir_links()
    print("  DDL da etapa 3 x gabarito ......... %d comandos" % a)
    print("  DDL da etapa 6 x gabarito ......... %d comandos" % b)
    print("  SQL da etapa 8 x dashboard/cards .. %d graficos" % c)
    print("  links e imagens nos .md ........... %d" % d)
    print()
    if erros:
        for e in erros:
            print("  %s❌%s %s" % (R, F, e))
        print()
        print("%s%d divergencia(s).%s" % (R, len(erros), F))
        return 1
    print("%s✅ Documentacao e gabaritos dizem a mesma coisa.%s" % (V, F))
    return 0


if __name__ == "__main__":
    sys.exit(main())
