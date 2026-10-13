# -*- coding: utf-8 -*-
"""
Segue a trilha EXATAMENTE como esta escrita nos READMEs.

Ferramenta de quem MANTEM o repositorio (o aluno nao precisa dela). Ela le
os READMEs na ordem da trilha e executa cada bloco de codigo marcado:

    <!-- rodar: shell -->   comando de terminal, na raiz do repositorio
    <!-- rodar: oltp -->    SQL colado no psql do banco transacional
    <!-- rodar: dw -->      SQL colado no psql do banco dimensional

Bloco sem marca (saida esperada, comando interativo, exemplo) e ignorado.
`<!-- rodar: shell falha-esperada -->` = o comando DEVE falhar (ex.: a
conferencia antes de o aluno fazer o trabalho).

`<!-- teste: comando -->` = comando que so este script roda, no lugar de um
trecho que o aluno faz com cliques (os dashboards, no Metabase).

Se a documentacao mandar o aluno fazer algo que nao funciona, este script
quebra. E assim que se garante que o passo a passo nao envelhece.

Uso (roda na SUA maquina, nao no container - ele chama docker e make):
    python3 tests/seguir_trilha.py                 # a trilha inteira
    python3 tests/seguir_trilha.py --listar        # so mostra os blocos
    python3 tests/seguir_trilha.py --de 3 --ate 4  # so as etapas 3 e 4
    python3 tests/seguir_trilha.py --comparar      # avisa onde a saida real
                                                   # difere da escrita no roteiro

Comece SEMPRE de um ambiente limpo:  make limpar && python3 tests/seguir_trilha.py
"""
import argparse
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (numero da etapa, arquivo)
TRILHA = [
    (0, "README.md"),
    (1, "modelagem/01_legado/README.md"),
    (2, "modelagem/02_demandas/README.md"),
    (3, "modelagem/03_evolucao_oltp/README.md"),
    (4, "data_simulator/README.md"),
    (5, "modelagem/04_dw_legado/README.md"),
    (6, "modelagem/05_evolucao_dw/README.md"),
    (7, "etl/README.md"),
    (8, "dashboard/README.md"),
]

PSQL = {
    "oltp": ["docker", "exec", "-i", "modelagem_oltp", "psql", "-v", "ON_ERROR_STOP=1",
             "-U", "sudoers", "-d", "liga_sudoers"],
    "dw": ["docker", "exec", "-i", "modelagem_dw", "psql", "-v", "ON_ERROR_STOP=1",
           "-U", "sudoers", "-d", "liga_sudoers_dw"],
}

MARCA = re.compile(r"<!--\s*rodar:\s*(\w+)([^>]*?)-->\s*\n```[\w]*\n(.*?)\n```"
                   r"|<!--\s*teste:\s*(.+?)\s*-->", re.S)
V, A, R, C, N, F = "\033[92m", "\033[93m", "\033[91m", "\033[90m", "\033[1m", "\033[0m"


SAIDA = re.compile(r"\A\s*(?:[^\n`<#]*\n){0,6}?\s*```\n(.*?)\n```", re.S)


def blocos_de(arquivo):
    with open(os.path.join(RAIZ, arquivo), encoding="utf-8") as fh:
        texto = fh.read()
    achados = list(MARCA.finditer(texto))
    for i, m in enumerate(achados):
        linha = texto.count("\n", 0, m.start()) + 1
        if m.group(4):      # <!-- teste: comando --> : substitui um trecho manual (cliques)
            yield {"tipo": "shell", "opcoes": ["so-no-teste"], "codigo": m.group(4), "linha": linha,
                   "esperado": None}
            continue
        # a "saida esperada" e o bloco SEM linguagem que vem logo depois do comando
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        s = SAIDA.match(texto[m.end():fim])
        yield {"tipo": m.group(1), "opcoes": m.group(2).split(), "codigo": m.group(3), "linha": linha,
               "esperado": s.group(1) if s else None}


def limpar(texto):
    texto = re.sub(r"\x1b\[[0-9;]*m", "", texto)
    return [re.sub(r"\s+", " ", l).strip() for l in texto.splitlines() if l.strip()]


def comparar(esperado, real):
    """Devolve None se a saida real contem a esperada; senao, a 1a linha que nao bateu.

    Uma linha so com "..." no esperado vale como "qualquer coisa aqui".
    """
    real = limpar(real)
    pos = 0
    for linha in limpar(esperado):
        if linha == "...":
            continue
        try:
            pos = real.index(linha, pos) + 1
        except ValueError:
            return linha
    return None


def executar(bloco, mostrar):
    if bloco["tipo"] == "shell":
        proc = subprocess.run(["bash", "-eo", "pipefail", "-c", bloco["codigo"]], cwd=RAIZ,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    else:
        proc = subprocess.run(PSQL[bloco["tipo"]], input=bloco["codigo"] + "\n", cwd=RAIZ,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    falhou = proc.returncode != 0
    esperava_falha = "falha-esperada" in bloco["opcoes"]
    ok = falhou == esperava_falha
    if mostrar or not ok:
        saida = proc.stdout.rstrip()
        if saida:
            print("\n".join("      " + linha for linha in saida.splitlines()[-mostrar if mostrar else -40:]))
    bloco["saida"] = proc.stdout
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--de", type=int, default=0)
    ap.add_argument("--ate", type=int, default=99)
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--mostrar", type=int, default=0, help="mostra as ultimas N linhas da saida de cada bloco")
    ap.add_argument("--comparar", action="store_true",
                    help="avisa quando a saida real difere da 'saida esperada' escrita no roteiro")
    args = ap.parse_args()

    total = diferentes = 0
    for etapa, arquivo in TRILHA:
        if not (args.de <= etapa <= args.ate):
            continue
        if not os.path.exists(os.path.join(RAIZ, arquivo)):
            print("%s(falta o arquivo %s)%s" % (R, arquivo, F))
            return 1
        print()
        print("%s== etapa %d: %s%s" % (N, etapa, arquivo, F))
        for b in blocos_de(arquivo):
            total += 1
            resumo = b["codigo"].strip().splitlines()[0][:90]
            rotulo = "%s:%d [%s%s]" % (arquivo, b["linha"], b["tipo"],
                                        " " + " ".join(b["opcoes"]) if b["opcoes"] else "")
            if args.listar:
                print("   %s%s%s  %s" % (C, rotulo, F, resumo))
                continue
            print("   %s▶ %s%s  %s" % (C, rotulo, F, resumo), flush=True)
            if not executar(b, args.mostrar):
                print()
                print("%s❌ A trilha quebrou em %s%s" % (R, rotulo, F))
                print("   bloco:\n" + "\n".join("      " + l for l in b["codigo"].splitlines()[:15]))
                return 1
            if args.comparar and b["esperado"]:
                nao_bateu = comparar(b["esperado"], b["saida"])
                if nao_bateu:
                    diferentes += 1
                    print("      %s≠ a saida real nao tem esta linha do roteiro:%s %s" % (A, F, nao_bateu[:120]))
    print()
    if not args.listar:
        print("%s✅ %d blocos executados sem erro.%s" % (V, total, F))
        if args.comparar:
            print("   %d bloco(s) com saida diferente da escrita no roteiro "
                  "(esperado onde ha sorteio ou data; revise os demais)." % diferentes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
