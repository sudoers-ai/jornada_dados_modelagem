# 👩‍💻 Perfis e responsabilidades

> ⬅️ [README principal](../README.md)

Nesta disciplina você faz, sozinho, o trabalho de quatro profissionais. Num
time de verdade eles são pessoas diferentes, e saber onde termina o trabalho
de um e começa o do outro é parte de ser sênior.

> **Dica:** ao fim de cada etapa, pergunte-se: "quem do time teria feito
> isto? E quem teria que ser avisado?"

---

## Database Administrator (DBA)

Cuida do banco **transacional**: o que você fez nas etapas 1 a 4.

**Responsabilidades:**

* Planejar e implementar a estrutura de bancos relacionais.
* Garantir normalização, integridade referencial e desempenho nas operações
  transacionais.
* Criar chaves, índices, restrições e triggers.
* Evoluir o modelo **sem derrubar o que está em produção**.
* Monitorar e otimizar o banco.

**Onde aparece na trilha:**

| Etapa | O que o DBA faz |
|---|---|
| 3 | Avalia cada `ALTER TABLE`: "essa coluna nova trava a tabela? Precisa de `DEFAULT`?" |
| 3 | Decide tipos (`numeric` para dinheiro, `char(2)` para UF) e chaves |
| 4 | Garante que os triggers de `updated_at` existem, porque o ETL depende deles |

**A pergunta que ele sempre faz:** "o que acontece com as linhas que já
existem?"

---

## Data Architect (Arquiteto de Dados)

Desenha os **modelos**: é quem escreveu os arquivos `.dbml` que você recebeu
prontos.

**Responsabilidades:**

* Traduzir demandas de negócio em modelos de dados.
* Decidir o que é entidade, o que é atributo e como se relacionam.
* Definir padrões: nomes, tipos, chaves substitutas, convenções.
* Garantir que o transacional e o dimensional contem a mesma história.

**Onde aparece na trilha:**

| Etapa | O que o arquiteto faz |
|---|---|
| 2 | Lê as três demandas e decide: `dispositivo` vira tabela; `carga_pedidos` resolve o N:N |
| 6 | Define o grão de cada fato e o tipo de cada dimensão (SCD 1 ou 2) |
| 6 | Decide que o preço mora na fato, e não na dimensão |

**A pergunta que ele sempre faz:** "o que é uma linha desta tabela?"

---

## Data Engineer / Data Warehouse Specialist

Constrói e mantém o **caminho** entre os dois modelos: as etapas 5 a 7.

**Responsabilidades:**

* Projetar e implementar esquemas dimensionais (star schema, snowflake).
* Desenvolver processos de ETL/ELT para extrair, transformar e carregar.
* Garantir que a carga seja idempotente, incremental e verificável.
* Integrar várias fontes e garantir qualidade e consistência.
* Monitorar e corrigir falhas nos pipelines.

**Onde aparece na trilha:**

| Etapa | O que o engenheiro faz |
|---|---|
| 5 | Descobre que o ETL legado conta o faturamento em dobro |
| 7 | Escreve cada `MERGE` e a prova que acompanha |
| 7 | Decide o intervalo da carga e o que fazer quando ela falha no meio |

**A pergunta que ele sempre faz:** "se isto rodar duas vezes, o que
acontece?"

---

## Analytics Engineer

Fica entre o engenheiro e o analista: transforma o DW em algo **pronto para
consumo** e cuida da definição das métricas.

**Responsabilidades:**

* Modelar as camadas analíticas (hoje, quase sempre com dbt).
* Definir cada métrica **uma vez**, num lugar só.
* Testar e documentar os modelos.

**Onde aparece na trilha:**

| Etapa | O que o analytics engineer faz |
|---|---|
| 6 e 7 | Cria `fato_peso_diario`, um agregado pensado para um dashboard |
| 7 | Tira a regra "área atendida" do gráfico e a coloca em `dim_localidade` |
| 8 | Percebe que "ticket médio" estava sendo calculado por produto |

**A pergunta que ele sempre faz:** "todo mundo calcula esse número do mesmo
jeito?"

---

## Data Analyst / BI Analyst

Transforma o DW em **decisão**: a etapa 8.

**Responsabilidades:**

* Criar visualizações e relatórios para a tomada de decisão.
* Usar ferramentas de BI (Metabase, Power BI, Tableau, Looker).
* Definir métricas e KPIs junto com as áreas de negócio.
* Transformar dados em recomendações.

**Onde aparece na trilha:**

| Etapa | O que o analista faz |
|---|---|
| 8 | Monta os dashboards Antifraude, Logística e Ciclo do pedido |
| 8 | Lê a tabela de transportadoras e conclui: a mais barata é a que mais atrasa |

**A pergunta que ele sempre faz:** "e daí? O que a gente faz com esse
número?"

---

## Quem avisa quem

A lição da etapa 8, em forma de tabela. Toda mudança de modelo tem alguém
"rio abaixo" que precisa saber:

| Quem mudou | O que mudou | Quem precisa ser avisado |
|---|---|---|
| DBA | Coluna nova no transacional | Engenheiro de dados (o ETL não a conhece) |
| Arquiteto | A fato perdeu a coluna `total` | Analista (quatro gráficos vão quebrar) |
| Engenheiro | `dim_pessoas` virou SCD tipo 2 | Todos que fazem `JOIN` nela pelo `id` |
| Engenheiro | O intervalo do ETL | Analista e áreas de negócio (o quão "de hoje" é o dashboard) |

O dashboard quebrado que você encontrou no início da etapa 8 é o que acontece
quando essa conversa não existe.
