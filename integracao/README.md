# 🔗 Integração com os outros repositórios (opcional)

> ⬅️ [README principal](../README.md)

> 🛑 **Nada aqui é necessário para concluir a disciplina.** Este repositório
> é autocontido, e a trilha termina nos [desafios](../desafios/desafios.md).
> Esta página é para quem **também** cursou as outras partes da Jornada e
> quer enxergar como elas se encaixam.

## O que os repositórios têm em comum

Os três usam o mesmo universo, a Liga Sudoers, gerado com a **mesma semente**.
A pessoa de `id = 1` é o Thomas Camargo em todos, e o pedido `1` é o mesmo
pedido. Isso não cria dependência: cada repositório carrega a sua própria
cópia do gerador.

| Repositório | O que ensina | O que tem de modelagem |
|---|---|---|
| [`liga_sudoers`](https://github.com/sudoers-ai/liga_sudoers) | OLTP, DW e ETL tradicionais (Apache Hop, Metabase) | As 6 tabelas do legado e o star schema original — o **ponto de partida** desta disciplina |
| [`jornada_dados`](https://github.com/sudoers-ai/jornada_dados) | CDC, Kafka, Spark, Delta Lake, dbt, Airflow | O mesmo legado, em camadas bronze, silver e gold |
| [`jornada_dados_nosql`](https://github.com/sudoers-ai/jornada_dados_nosql) | Cinco bancos não relacionais | O mesmo pedido em cinco modelos diferentes |
| **este** | Modelagem transacional e dimensional | A evolução dos dois modelos |

## Ideia 1 — Levar o modelo novo para o pipeline do `jornada_dados`

O `jornada_dados` move o legado de 6 tabelas por Debezium → Kafka → Spark →
Delta. O modelo desta disciplina cabe lá sem mudar a arquitetura.

Com o `jornada_dados` no ar, aplique a evolução no transacional **dele**:

```bash
docker exec -i postgres_oltp psql -U sudoers -d liga_sudoers \
  < modelagem/ddl/gabarito/oltp_evolucao.sql
```

O arquivo só acrescenta tabelas e colunas, então os pipelines que já existem
lá continuam funcionando. A partir daí:

* inclua as tabelas novas no conector do Debezium (`table.include.list`);
* crie os modelos `bronze` das tabelas novas no dbt;
* reescreva os passos de `etl/sql/` como modelos `silver` (dimensões) e `gold`
  (fatos). O `MERGE` daqui vira `materialized='incremental'` com
  `unique_key` lá.

É um bom exercício de nível Sênior: o **desenho** é o mesmo; muda a
ferramenta que executa a transformação.

> As senhas dos bancos são diferentes entre os repositórios (`password` aqui,
> `sudoers` no `jornada_dados`). Os simuladores daqui apontam para os
> containers daqui; para gerar dados lá, use os geradores de lá.

## Ideia 2 — O score de risco do grafo como atributo de dimensão

No `jornada_dados_nosql`, o Neo4j calcula um **score de risco por pessoa** a
partir da rede de contas e aparelhos, e o exporta em Parquet. Como os `id` de
pessoa são os mesmos, esse score pode entrar em `dim_pessoas` como mais um
atributo:

```sql
ALTER TABLE dim_pessoas ADD COLUMN score_risco numeric(5,2);
```

Compare com o `is_compartilhado` de `dim_dispositivo`, que você calculou em
SQL: os dois respondem à mesma pergunta por caminhos diferentes. O SQL acha
quem **compartilha um aparelho**; o grafo acha também quem está **a dois
saltos** de alguém que compartilha.

## Ideia 3 — O mesmo pedido em sete modelos

Somando as partes, o pedido `1` existe como:

| Onde | Forma |
|---|---|
| Transacional (aqui) | linhas em 7 tabelas normalizadas |
| Dimensional (aqui) | linhas em 3 fatos, apontando para 7 dimensões |
| MongoDB | um documento, com itens e auditoria embutidos |
| Redis | chaves de consulta rápida |
| Neo4j | nós e relações |
| Cassandra | linhas em tabelas desenhadas por consulta |
| ClickHouse | uma linha larga numa tabela colunar |

Nenhum é "o certo". Cada um otimiza uma pergunta. Depois desta disciplina,
você sabe dizer qual pergunta os dois primeiros otimizam — e é o mesmo
raciocínio que escolhe entre os outros cinco.

## Ideia 4 — Um laboratório para treinar SQL analítico

O DW que você construiu é um bom lugar para praticar funções de janela,
`GROUPING SETS`, `FILTER` e CTEs — os assuntos do
[`jornada_dados_sql`](https://github.com/sudoers-ai/jornada_dados_sql). Três
perguntas para começar:

1. Para cada transportadora, a média móvel de 7 dias do percentual de atraso.
2. O ranking de clientes por faturamento dentro de cada UF, com a posição.
3. Para cada pedido, quantos dias se passaram desde o pedido anterior do
   mesmo cliente.
