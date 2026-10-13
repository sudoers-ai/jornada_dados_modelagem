# -*- coding: utf-8 -*-
"""
Extensao do universo Liga Sudoers para a disciplina de Modelagem.

O gerador canonico (liga_sudoers_gen.py) conhece pessoas, produtos e
pedidos. As tres demandas desta disciplina pedem mais do que isso:

    Demanda 1 (antifraude)  -> dispositivos, resultado da analise de fraude
    Demanda 2 (logistica)   -> peso, enderecos, transportadoras, transportes
    Demanda 3 (ciclo)       -> pagamentos e historico de status

Este modulo deriva tudo isso do universo canonico, tambem de forma
DETERMINISTICA: mesma semente, exatamente os mesmos dados.

A linha do tempo e a do gerador (o "hoje" dele e fixo em 01/09/2026). Quem
carrega os dados desloca todas as datas para que o "hoje" do gerador vire o
agora de verdade - assim "ultimos 7 dias" sempre tem dado.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from faker import Faker

from gerador.liga_sudoers_gen import UF_LEGITIMAS, _so_do_modelo

HOJE_GERADOR = datetime(2026, 9, 1, 12, 0, 0)
DIAS_HISTORICO = 180

# --------------------------------------------------------------------------
# Regras de negocio da simulacao
# --------------------------------------------------------------------------

# Faixa de peso (gramas) por categoria de produto
FAIXA_PESO = {
    1: (200, 8000),      # Eletronicos
    2: (100, 900),       # Vestuario
    3: (150, 1200),      # Livros
    4: (100, 5000),      # Alimentos
    5: (3000, 45000),    # Moveis
    6: (100, 6000),      # Informatica
    7: (50, 800),        # Beleza
    8: (200, 9000),      # Esportes
    9: (100, 3000),      # Brinquedos
    10: (300, 12000),    # Ferramentas
    11: (300, 20000),    # Automotivo
    12: (100, 15000),    # Pet
}

# `taxa_atraso` NAO vai para o banco: e o comportamento "escondido" de cada
# transportadora, que o aluno vai DESCOBRIR no dashboard de logistica.
# Repare na Barato Fretes: a mais barata por kg, e a que mais atrasa.
TRANSPORTADORAS = [
    {"id": 1, "nome": "Rápido Bandeirante", "cnpj": "12.345.678/0001-10", "custo_por_kg": 4.90, "taxa_atraso": 0.10},
    {"id": 2, "nome": "TransMinas Cargas",  "cnpj": "23.456.789/0001-21", "custo_por_kg": 5.60, "taxa_atraso": 0.12},
    {"id": 3, "nome": "Expresso Carioca",   "cnpj": "34.567.890/0001-32", "custo_por_kg": 6.20, "taxa_atraso": 0.08},
    {"id": 4, "nome": "Sudeste Log",        "cnpj": "45.678.901/0001-43", "custo_por_kg": 7.80, "taxa_atraso": 0.03},
    {"id": 5, "nome": "Barato Fretes",      "cnpj": "56.789.012/0001-54", "custo_por_kg": 3.20, "taxa_atraso": 0.45},
]
ID_TRANSPORTADORA_LENTA = 5

# Peso de sorteio de cada transportadora por UF de destino
PREFERENCIA_UF = {
    "SP": {1: 40, 2: 5,  3: 5,  4: 20, 5: 30},
    "MG": {1: 10, 2: 40, 3: 5,  4: 20, 5: 25},
    "RJ": {1: 10, 2: 5,  3: 40, 4: 20, 5: 25},
}

# O centro de distribuicao fica em SP: prazo de entrega (dias) por UF
PRAZO_DIAS = {"SP": 2, "RJ": 3, "MG": 4}

CAPACIDADE_CAMINHAO = 12      # pedidos por transporte
FRETE_MINIMO = 25.00

FORMAS_PAGAMENTO = ("pix", "cartao_credito", "boleto", "cartao_debito")
PESO_FORMA_NORMAL = (40, 38, 14, 8)
PESO_FORMA_FRAUDE = (10, 80, 2, 8)     # fraude prefere cartao de credito

TAXA_PAGAMENTO_RECUSADO = 0.04
TAXA_BOLETO_NAO_PAGO = 0.08
DIAS_VENCIMENTO_BOLETO = 4
TAXA_DEVOLUCAO = 0.03
TAXA_MUDANCA_ENDERECO = 0.15

STATUS_FINAIS = ("entregue", "cancelado", "devolvido")


def sortear_transportadora(uf: str, rnd: random.Random) -> dict:
    pesos = PREFERENCIA_UF.get(uf, PREFERENCIA_UF["SP"])
    ids = list(pesos)
    escolhido = rnd.choices(ids, weights=[pesos[i] for i in ids])[0]
    return TRANSPORTADORAS[escolhido - 1]


def sortear_placa(rnd: random.Random) -> str:
    letras = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "%s%s%s%d%s%d%d" % (rnd.choice(letras), rnd.choice(letras), rnd.choice(letras),
                               rnd.randint(0, 9), rnd.choice(letras),
                               rnd.randint(0, 9), rnd.randint(0, 9))


def calcular_frete(peso_gramas: int, custo_por_kg: float) -> float:
    return round(max(peso_gramas / 1000.0 * custo_por_kg, FRETE_MINIMO), 2)


def sortear_pagamento(fraude: bool, rnd: random.Random) -> tuple:
    """Devolve (forma, parcelas)."""
    pesos = PESO_FORMA_FRAUDE if fraude else PESO_FORMA_NORMAL
    forma = rnd.choices(FORMAS_PAGAMENTO, weights=pesos)[0]
    parcelas = 1
    if forma == "cartao_credito":
        parcelas = rnd.choice([6, 10, 12]) if fraude else rnd.choice([1, 1, 1, 2, 3, 3, 6, 10, 12])
    return forma, parcelas


def estender(u) -> dict:
    """Recebe o Universo canonico e devolve as tabelas novas, ja coerentes.

    Tudo em datetime na linha do tempo do GERADOR (hoje = HOJE_GERADOR).
    So existe no resultado o que ja "aconteceu" ate o hoje do gerador:
    um pedido feito ontem ainda nao foi entregue, por exemplo.
    """
    rnd = random.Random(u.semente * 1000 + 7)
    fake = Faker("pt_BR")
    fake.seed_instance(u.semente * 1000 + 7)

    hoje = HOJE_GERADOR
    inicio = hoje - timedelta(days=DIAS_HISTORICO)

    # ---------------------------------------------------------------- pesos
    pesos = {}
    for p in u.produtos:
        minimo, maximo = FAIXA_PESO[p["id_categoria"]]
        pesos[p["id"]] = rnd.randint(minimo // 50, maximo // 50) * 50

    # ------------------------------------------------------------ enderecos
    # ~15% das pessoas se mudaram de cidade durante o historico. Elas tem
    # DOIS enderecos: o antigo (is_principal = false) e o atual.
    enderecos = []
    linha_do_tempo_endereco = {}      # id_pessoa -> [(valido_desde, id_endereco, uf)]
    prox_endereco = 1
    for p in u.pessoas:
        cadastro = datetime.fromisoformat(p["created_at"])
        versoes = []
        if rnd.random() < TAXA_MUDANCA_ENDERECO:
            dt_mudanca = inicio + timedelta(days=rnd.randint(20, 160), seconds=rnd.randint(0, 86399))
            cidade_antiga = fake.city()
            while cidade_antiga == p["cidade"]:
                cidade_antiga = fake.city()
            enderecos.append({
                "id": prox_endereco, "id_pessoa": p["id"],
                "logradouro": fake.street_address(), "cidade": cidade_antiga, "uf": p["uf"],
                "cep": fake.postcode(), "is_principal": False,
                "created_at": cadastro, "updated_at": dt_mudanca,
            })
            versoes.append((cadastro, prox_endereco, p["uf"]))
            prox_endereco += 1
            desde = dt_mudanca
        else:
            desde = cadastro
        enderecos.append({
            "id": prox_endereco, "id_pessoa": p["id"],
            "logradouro": fake.street_address(), "cidade": p["cidade"], "uf": p["uf"],
            "cep": fake.postcode(), "is_principal": True,
            "created_at": desde, "updated_at": desde,
        })
        versoes.append((desde, prox_endereco, p["uf"]))
        prox_endereco += 1
        linha_do_tempo_endereco[p["id"]] = versoes

    def endereco_em(id_pessoa, quando):
        """O endereco em que a pessoa morava naquela data."""
        vigente = linha_do_tempo_endereco[id_pessoa][0]
        for versao in linha_do_tempo_endereco[id_pessoa]:
            if versao[0] <= quando:
                vigente = versao
        return vigente[1], vigente[2]

    # --------------------------------------------------------- dispositivos
    # O catalogo do gerador so tem os aparelhos "de sempre". Os aparelhos
    # usados UMA vez numa troca de dispositivo aparecem so nos pedidos.
    dispositivos = {}
    for d in u.dispositivos:
        dispositivos[d["device_id"]] = {"device_id": d["device_id"], "modelo": d["modelo"],
                                        "sistema": d["so"], "created_at": inicio}
    for ped in u.pedidos:
        a = ped["auditoria"]
        if a["device_id"] not in dispositivos:
            dispositivos[a["device_id"]] = {
                "device_id": a["device_id"], "modelo": a["dispositivo"],
                "sistema": _so_do_modelo(a["dispositivo"]),
                "created_at": datetime.fromisoformat(ped["dt_venda"]),
            }

    # ------------------------------------- pedidos: pagamento, fraude, status
    pedidos_ext, pagamentos, status = {}, [], []
    fila_expedicao = []            # pedidos separados, esperando caminhao

    for ped in u.pedidos:
        dt_venda = datetime.fromisoformat(ped["dt_venda"])
        id_endereco, uf_destino = endereco_em(ped["id_pessoa"], dt_venda)
        peso = sum(it["qtde"] * pesos[it["id_produto"]] for it in ped["itens"])
        fraude = ped["fraude"]

        forma, parcelas = sortear_pagamento(fraude, rnd)
        recusado = (not fraude) and rnd.random() < TAXA_PAGAMENTO_RECUSADO
        nao_paga = forma == "boleto" and rnd.random() < TAXA_BOLETO_NAO_PAGO
        if forma == "boleto":
            demora = timedelta(hours=rnd.uniform(6, 72))
        else:
            demora = timedelta(seconds=rnd.randint(20, 600))
        dt_pag = dt_venda + demora
        dt_fraude = dt_venda + timedelta(hours=rnd.uniform(2, 96)) if fraude else None
        dt_sep = dt_pag + timedelta(hours=rnd.uniform(2, 36))
        vai_devolver = rnd.random() < TAXA_DEVOLUCAO
        dias_ate_devolucao = rnd.uniform(2, 10)

        eventos = [("criado", dt_venda)]
        pag = {"status": "pendente", "dt_pagamento": None}
        fraude_confirmada = bool(fraude and dt_fraude <= hoje)

        if nao_paga:
            vencimento = dt_venda + timedelta(days=DIAS_VENCIMENTO_BOLETO)
            if vencimento <= hoje:
                pag = {"status": "expirado", "dt_pagamento": None}
                eventos.append(("cancelado", vencimento))
        elif dt_pag <= hoje:
            if recusado:
                pag = {"status": "recusado", "dt_pagamento": dt_pag}
                eventos.append(("cancelado", dt_pag))
            else:
                pag = {"status": "aprovado", "dt_pagamento": dt_pag}
                eventos.append(("pago", dt_pag))
                # o caminhao sai no dia seguinte a separacao, de manha
                saida_minima = (dt_sep + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
                if fraude_confirmada and dt_fraude < saida_minima:
                    # fraude descoberta a tempo: o pedido nem sai do galpao
                    pag["status"] = "estornado"
                    if dt_sep <= hoje and dt_sep < dt_fraude:
                        eventos.append(("separado", dt_sep))
                    eventos.append(("cancelado", dt_fraude))
                elif dt_sep <= hoje:
                    eventos.append(("separado", dt_sep))
                    fila_expedicao.append((saida_minima.date(), uf_destino, ped["id"]))
                    if fraude_confirmada:
                        pag["status"] = "estornado"     # descoberta tarde demais: prejuizo

        pedidos_ext[ped["id"]] = {
            "id_endereco_entrega": id_endereco, "uf_destino": uf_destino, "peso_gramas": peso,
            "eventos": eventos, "fraude_confirmada": fraude_confirmada,
            "dt_fraude": dt_fraude if fraude_confirmada else None,
            "motivo_fraude": ped["motivo_fraude"] if fraude_confirmada else None,
            "pagamento": pag, "vai_devolver": vai_devolver and not fraude,
            "dias_ate_devolucao": dias_ate_devolucao, "valor_total": ped["valor_total"],
            "forma": forma, "parcelas": parcelas, "dt_venda": dt_venda,
        }

    # ------------------------------------------------- transportes e cargas
    # Os pedidos separados sao agrupados por dia de saida e UF de destino.
    # Cada grupo vira um ou mais caminhoes.
    grupos = {}
    for dia, uf, id_pedido in fila_expedicao:
        grupos.setdefault((dia, uf), []).append(id_pedido)

    transportes, cargas = [], []
    prox_transporte = 1
    for (dia, uf) in sorted(grupos):
        ids = grupos[(dia, uf)]
        for i in range(0, len(ids), CAPACIDADE_CAMINHAO):
            lote = ids[i:i + CAPACIDADE_CAMINHAO]
            t = sortear_transportadora(uf, rnd)
            dt_saida = datetime(dia.year, dia.month, dia.day, 6, 0, 0) + timedelta(minutes=rnd.randint(0, 360))
            prazo = PRAZO_DIAS[uf]
            dt_prevista = dt_saida + timedelta(days=prazo)
            if rnd.random() < t["taxa_atraso"]:
                dt_real = dt_prevista + timedelta(hours=rnd.uniform(6, 96))
            else:
                dt_real = dt_prevista - timedelta(hours=rnd.uniform(1, 20))
            placa = sortear_placa(rnd)
            if dt_saida > hoje:
                continue                    # o caminhao ainda nao saiu: segue "separado"

            peso_total = sum(pedidos_ext[i]["peso_gramas"] for i in lote)
            entregue = dt_real <= hoje
            transportes.append({
                "id": prox_transporte, "id_transportadora": t["id"], "placa": placa,
                "peso_total_gramas": peso_total,
                "valor_frete": calcular_frete(peso_total, t["custo_por_kg"]),
                "dt_saida": dt_saida, "dt_entrega_prevista": dt_prevista,
                "dt_entrega": dt_real if entregue else None,
            })
            for id_pedido in lote:
                cargas.append({"id_transporte": prox_transporte, "id_pedido": id_pedido, "dt": dt_saida})
                ext = pedidos_ext[id_pedido]
                ext["eventos"].append(("enviado", dt_saida))
                if entregue:
                    ext["eventos"].append(("entregue", dt_real))
                    if ext["vai_devolver"]:
                        dt_dev = dt_real + timedelta(days=ext["dias_ate_devolucao"])
                        if dt_dev <= hoje:
                            ext["eventos"].append(("devolvido", dt_dev))
                            ext["pagamento"]["status"] = "estornado"
            prox_transporte += 1

    # --------------------------------------------- consolida status e pagto
    prox_pagamento = 1
    for ped in u.pedidos:
        ext = pedidos_ext[ped["id"]]
        ext["eventos"].sort(key=lambda e: e[1])
        ext["status"] = ext["eventos"][-1][0]
        ext["dt_ultimo_evento"] = ext["eventos"][-1][1]
        for nome, quando in ext["eventos"]:
            status.append({"id_pedido": ped["id"], "status": nome, "dt_evento": quando})
        pagamentos.append({
            "id": prox_pagamento, "id_pedido": ped["id"], "forma": ext["forma"],
            "parcelas": ext["parcelas"], "valor": ext["valor_total"],
            "status": ext["pagamento"]["status"], "dt_pagamento": ext["pagamento"]["dt_pagamento"],
            "created_at": ext["dt_venda"],
            "updated_at": max(ext["dt_ultimo_evento"], ext["pagamento"]["dt_pagamento"] or ext["dt_venda"]),
        })
        prox_pagamento += 1

    return {
        "pesos": pesos,
        "enderecos": enderecos,
        "dispositivos": [dispositivos[k] for k in sorted(dispositivos)],
        "transportadoras": TRANSPORTADORAS,
        "pedidos": pedidos_ext,
        "pagamentos": pagamentos,
        "status": status,
        "transportes": transportes,
        "cargas": cargas,
    }


def resumo(u, ext) -> dict:
    """Numeros do universo estendido. E a referencia do `make validar`."""
    por_status = {}
    for p in ext["pedidos"].values():
        por_status[p["status"]] = por_status.get(p["status"], 0) + 1
    return {
        "categorias": len(u.categorias),
        "produtos": len(u.produtos),
        "pessoas": len(u.pessoas),
        "enderecos": len(ext["enderecos"]),
        "dispositivos": len(ext["dispositivos"]),
        "transportadoras": len(ext["transportadoras"]),
        "pedidos": len(u.pedidos),
        "itens_pedidos": sum(len(p["itens"]) for p in u.pedidos),
        "auditoria_pedidos": len(u.pedidos),
        "pagamentos": len(ext["pagamentos"]),
        "status_pedidos": len(ext["status"]),
        "transportes": len(ext["transportes"]),
        "carga_pedidos": len(ext["cargas"]),
        "fraudes_confirmadas": sum(1 for p in ext["pedidos"].values() if p["fraude_confirmada"]),
        "pessoas_que_se_mudaram": sum(1 for e in ext["enderecos"] if not e["is_principal"]),
        "pedidos_por_status": dict(sorted(por_status.items())),
    }


if __name__ == "__main__":
    import json
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from gerador.liga_sudoers_gen import gerar_universo
    universo = gerar_universo()
    print(json.dumps(resumo(universo, estender(universo)), ensure_ascii=False, indent=2))
