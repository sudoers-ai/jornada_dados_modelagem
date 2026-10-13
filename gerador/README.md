# Gerador — de onde vêm os dados

> ⬅️ [README principal](../README.md) · usado na [etapa 4](../data_simulator/README.md)

Você não precisa rodar nada desta pasta: quem usa é o
`liga_sudoers_historico.py`. Ela está aqui para quem quiser entender (ou
mudar) as regras da simulação.

| Arquivo | Papel |
|---|---|
| `liga_sudoers_gen.py` | O gerador canônico da Jornada: pessoas, produtos, pedidos e as três fraudes plantadas. É uma **cópia fiel** do arquivo de mesmo nome do `jornada_dados_nosql` |
| `extensao_modelagem.py` | O que esta disciplina acrescenta: peso dos produtos, endereços, pagamentos, situações do pedido, transportadoras e transportes |
| `exportar_base.py` | Gera o cadastro base do legado (`modelagem/ddl/legado/02_oltp_dados_base.sql`). Só para quem mantém o repositório |

## Por que os dados são sempre os mesmos

O gerador é **determinístico**: com a mesma semente (42), produz exatamente
as mesmas pessoas, os mesmos pedidos e as mesmas fraudes. É isso que permite
ao roteiro mostrar a saída esperada e ao `make validar` conferir contagens
exatas.

É também a mesma semente dos outros repositórios da Jornada. A pessoa de
`id = 1` é o Thomas Camargo aqui, no `jornada_dados` e no
`jornada_dados_nosql` — sem que nenhum deles dependa do outro.

O gerador trabalha com uma data fixa. Na hora de gravar, o
`liga_sudoers_historico.py` desloca todas as datas para que o histórico
termine **agora**: os 180 dias são sempre os últimos 180.

## Veja o universo sem gravar nada

```bash
docker compose run --rm ferramentas python gerador/extensao_modelagem.py
```

```json
{
  "categorias": 12,
  "produtos": 200,
  "pessoas": 500,
  "enderecos": 578,
  "dispositivos": 583,
  "transportadoras": 5,
  "pedidos": 5000,
  "itens_pedidos": 14976,
  "auditoria_pedidos": 5000,
  "pagamentos": 5000,
  "status_pedidos": 24081,
  "transportes": 590,
  "carga_pedidos": 4629,
  "fraudes_confirmadas": 234,
  "pessoas_que_se_mudaram": 78,
  "pedidos_por_status": {
    "cancelado": 329,
    "criado": 9,
    "devolvido": 128,
    "entregue": 4421,
    "enviado": 80,
    "pago": 20,
    "separado": 13
  }
}
```

## As regras da simulação

Estão no topo do `extensao_modelagem.py`, em constantes com nome em
português. As principais:

| Regra | Valor |
|---|---|
| Pessoas que se mudaram durante o histórico | 15% |
| Pagamentos recusados | 4% |
| Boletos que nunca são pagos | 8% (o pedido é cancelado em 4 dias) |
| Pedidos devolvidos depois de entregues | 3% |
| Pedidos por caminhão | até 12 |
| Prazo de entrega | SP 2 dias, RJ 3, MG 4 |
| Frete | peso em kg × custo por kg da transportadora (mínimo R$ 25,00) |

E as três fraudes, herdadas do gerador canônico:

| Motivo | Como é plantada |
|---|---|
| `geolocalizacao` | pedido feito de fora de SP, MG e RJ |
| `troca_dispositivo` | pedido feito de um aparelho que a pessoa nunca usou |
| `dispositivo_compartilhado` | 6 anéis de 5 contas usando o mesmo aparelho físico |

Há também um comportamento que **não está em coluna nenhuma**: cada
transportadora tem uma taxa de atraso própria (`taxa_atraso`). É de propósito.
Você não a encontra no banco — você a **descobre**, no dashboard de Logística.

## Mudar o tamanho do universo (opcional)

No arquivo `.env`:

```bash
SEMENTE=42
N_PEDIDOS=5000
```

Depois, `make historico args=--limpar`. Atenção: com outros valores, as
contagens deixam de bater com as do roteiro.
