# Modelagem — o que há nesta pasta

> ⬅️ [README principal](../README.md)

Esta pasta guarda os **modelos** da disciplina e os roteiros das etapas que
mexem neles.

## As etapas

| # | Pasta | O que você faz |
|---|---|---|
| 1 | [`01_legado/`](./01_legado/README.md) | Conhece o transacional e o dimensional de hoje |
| 2 | [`02_demandas/`](./02_demandas/README.md) | Lê as três demandas e o modelo que as atende |
| 3 | [`03_evolucao_oltp/`](./03_evolucao_oltp/README.md) | Evolui o transacional |
| 5 | [`04_dw_legado/`](./04_dw_legado/README.md) | Carrega o DW antigo e descobre onde ele mente |
| 6 | [`05_evolucao_dw/`](./05_evolucao_dw/README.md) | Evolui o dimensional |

(A etapa 4 fica em [`data_simulator/`](../data_simulator/README.md), a 7 em
[`etl/`](../etl/README.md) e a 8 em [`dashboard/`](../dashboard/README.md).)

## Os modelos

Em [`dbml/`](./dbml/), no formato do [dbdiagram.io](https://dbdiagram.io).
Para ver como diagrama, cole o conteúdo do arquivo em
[dbdiagram.io/d](https://dbdiagram.io/d).

| Arquivo | O que é | Imagem |
|---|---|---|
| [`01_oltp_legado.dbml`](./dbml/01_oltp_legado.dbml) | O transacional de partida: 6 tabelas | [svg](./img/01_oltp_legado.svg) |
| [`02_oltp_evoluido.dbml`](./dbml/02_oltp_evoluido.dbml) | **O alvo da etapa 3**: 13 tabelas | [svg](./img/02_oltp_evoluido.svg) |
| [`03_dw_legado.dbml`](./dbml/03_dw_legado.dbml) | O dimensional de partida | [svg](./img/03_dw_legado.svg) |
| [`04_dw_evoluido.dbml`](./dbml/04_dw_evoluido.dbml) | **O alvo da etapa 6**: 7 dimensões e 4 fatos | [svg](./img/04_dw_evoluido.svg) |

Os arquivos `02` e `04` não são só documentação: os comandos
`make conferir-oltp` e `make conferir-dw` leem esses arquivos e comparam com
o seu banco. **O `.dbml` é o contrato.**

## Os scripts SQL

Em [`ddl/`](./ddl/):

| Pasta | Conteúdo | Quem roda |
|---|---|---|
| `ddl/legado/` | O ponto de partida dos dois bancos | O Docker, sozinho, na primeira subida |
| `ddl/gabarito/` | A resposta das etapas 3 e 6 | Você, com `make gabarito-oltp` ou `make gabarito-dw`, se travar |

## Para quem mantém o repositório

Depois de alterar um `.dbml`, regenere as imagens:

```bash
bash scripts/gerar_diagramas.sh
```

E confira se os roteiros e os gabaritos continuam dizendo a mesma coisa:

```bash
python3 tests/conferir_docs.py       # roteiros x gabaritos x links
make limpar
python3 tests/seguir_trilha.py       # executa a trilha inteira, como está escrita
```
