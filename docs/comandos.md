# ⌨️ Comandos

> ⬅️ [README principal](../README.md)

Todo `make` deste repositório é um atalho para um ou mais comandos `docker`.
Esta página mostra o que está por trás de cada um: serve para entender o que
o atalho faz e para investigar quando algo dá errado. Rode sempre na **pasta
raiz** do repositório.

> O `make` é pré-requisito da trilha. Se você ainda não tem, veja os
> [pré-requisitos](../README.md#-pré-requisitos). No Windows, tudo desta
> página é digitado no terminal do Ubuntu (WSL): veja
> [Preparando o Windows](./windows.md).

## Ambiente

| `make` | Comando equivalente |
|---|---|
| `make verificar` | `bash scripts/verificar.sh` |
| `make subir` | `docker compose up -d --build` e `docker compose build ferramentas` |
| `make status` | `docker compose ps -a` |
| `make derruba` | `docker compose --profile streaming --profile ferramentas down` |
| `make limpar` | `docker compose --profile streaming --profile ferramentas down -v` |
| `make logs s=metabase` | `docker compose logs -f metabase` |
| `make consertar` | `docker compose up -d --force-recreate` |
| `make diagnostico` | `bash scripts/diagnostico.sh` |

## Entrar nos bancos

| `make` | Comando equivalente |
|---|---|
| `make psql-oltp` | `docker exec -it modelagem_oltp psql -U sudoers -d liga_sudoers` |
| `make psql-dw` | `docker exec -it modelagem_dw psql -U sudoers -d liga_sudoers_dw` |
| `make sql-oltp f=arquivo.sql` | `docker exec -i modelagem_oltp psql -v ON_ERROR_STOP=1 -U sudoers -d liga_sudoers -f /repo/arquivo.sql` |
| `make sql-dw f=arquivo.sql` | `docker exec -i modelagem_dw psql -v ON_ERROR_STOP=1 -U sudoers -d liga_sudoers_dw -f /repo/arquivo.sql` |

> Dentro dos containers dos bancos, a pasta do repositório aparece em `/repo`
> (somente leitura).

Dentro do `psql`:

| Comando | Faz |
|---|---|
| `\dt` | lista as tabelas |
| `\d tabela` | descreve uma tabela (colunas, chaves, triggers) |
| `\dn` | lista os schemas |
| `\dt stg.*` | lista as tabelas de um schema |
| `\x` | liga/desliga a exibição "em pé" (boa para linhas largas) |
| `\q` | sai |

## Conferência e validação

| `make` | Comando equivalente |
|---|---|
| `make conferir-oltp` | `docker compose run --rm ferramentas python data_simulator/verificador.py oltp` |
| `make conferir-dw` | `docker compose run --rm ferramentas python data_simulator/verificador.py dw` |
| `make validar` | `docker compose run --rm ferramentas python tests/validar.py` |
| `make conferir-dashboards` | `docker compose run --rm ferramentas python dashboard/metabase.py conferir` |
| `make metabase-sync` | `docker compose run --rm ferramentas python dashboard/metabase.py sync` |

## Geração de dados

| `make` | Comando equivalente |
|---|---|
| `make historico` | `docker compose run --rm ferramentas python data_simulator/liga_sudoers_historico.py` |
| `make historico args=--limpar` | `... liga_sudoers_historico.py --limpar` |
| `make streaming` | `docker compose run --rm ferramentas python data_simulator/liga_sudoers_streaming.py` |
| `make streaming ciclos=5` | `... liga_sudoers_streaming.py --ciclos 5` |
| `make streaming-fundo` | `docker compose --profile streaming up -d streaming` |
| `make streaming-logs` | `docker compose --profile streaming logs -f --tail 30 streaming` |
| `make streaming-parar` | `docker compose --profile streaming rm -sf streaming` |

## ETL

| `make` | Comando equivalente |
|---|---|
| `make etl-legado` | roda `etl/sql/00_conexao_oltp.sql` e `etl/legado/etl_legado.sql` no DW |
| `make etl-passo p=08` | `docker exec -i modelagem_dw psql -v ON_ERROR_STOP=1 -U sudoers -d liga_sudoers_dw -f /repo/etl/sql/08_dim_pessoas.sql` |
| `make etl` | confere o DW e roda todos os arquivos de `etl/sql/`, em ordem |

## Gabaritos e recomeços

| `make` | O que faz |
|---|---|
| `make gabarito-oltp` | Aplica `modelagem/ddl/gabarito/oltp_evolucao.sql` no transacional |
| `make gabarito-dw` | Aplica `modelagem/ddl/gabarito/dw_evolucao.sql` no DW |
| `make gabarito-dashboards` | Conserta os gráficos antigos e cria os dashboards novos pela API do Metabase |
| `make reset-oltp` | Volta o transacional ao legado (6 tabelas, sem pedidos). **Apaga os dados dele** |
| `make reset-dw` | Volta o DW ao legado (vazio). **Apaga os dados dele** |
| `make limpar` | Apaga **tudo**, inclusive o Metabase. Depois, `make subir` recomeça do zero |

## Trocar uma porta

Se `make verificar` disser que uma porta está ocupada, edite o arquivo `.env`
(ele é criado sozinho na primeira vez) e rode `make subir` de novo:

```bash
PORTA_OLTP=5440
PORTA_DW=5441
PORTA_METABASE=3020
```

Se trocar a `PORTA_METABASE`, o endereço do Metabase muda junto
(`http://localhost:<a porta que você escolheu>`).
