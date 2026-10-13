# 🧪 Desafios da Jornada — Modelagem de Dados

> ⬅️ Anterior: [8. Dashboards](../dashboard/README.md) · [README principal](../README.md) · Etapa 9 de 9

A trilha guiada acabou. Aqui não há passo a passo: há o problema, o que conta
como evidência e o que entregar.

Escolha o seu nível. Cada desafio tem **tarefas**, **evidências** (o que
comprova que deu certo) e **entregáveis** (o que você vai postar ou commitar).

- [Nível Júnior](#-nível-júnior) — a trilha de ponta a ponta, explicada com as suas palavras
- [Nível Pleno](#-nível-pleno) — modelar sem roteiro
- [Nível Sênior](#-nível-sênior) — decisões de arquitetura, qualidade e operação

> **Dica:** conclua o Júnior antes, mesmo que você seja avançado. Ele garante
> que o ambiente está consistente, e os outros níveis partem dele.
>
> **Onde colocar o seu trabalho:** crie uma pasta `entregas/` na raiz do
> repositório. Não é preciso alterar nenhum arquivo do projeto. Para rodar um
> SQL seu: `make sql-oltp f=entregas/arquivo.sql` ou
> `make sql-dw f=entregas/arquivo.sql`.

---

## 🔹 Nível Júnior

**Foco:** percorrer a trilha inteira e provar que entendeu o porquê de cada
transformação.

### Tarefas

1. Concluir as etapas 1 a 8 **sem usar nenhum gabarito**.
2. Rodar os três comandos de prova e guardar a saída:
   `make conferir-oltp`, `make validar` e `make conferir-dashboards`.
3. Preencher, com as suas palavras, a tabela de transformação: para **cada
   tabela do dimensional**, de quais tabelas do transacional ela veio e o que
   mudou no caminho.
4. Escrever, em uma frase cada, o **grão** das quatro fatos.
5. Criar **um gráfico novo, de sua autoria**, em qualquer dashboard, que use
   pelo menos uma dimensão criada nesta disciplina. Sugestão: faturamento por
   fabricante do aparelho.
6. Responder: por que o faturamento do DW antigo era quase quatro vezes o
   real? Mostre com um pedido de exemplo (não o pedido 1).

### Evidências mínimas

* Saída de `make conferir-oltp` e `make conferir-dw` com **0 pendências**.
* Saída de `make validar` com **41 passaram, 0 falharam**.
* Saída de `make conferir-dashboards` com **✅ Dashboards conferidos**.
* *Print* dos cinco dashboards.
* *Print* do seu gráfico novo, com o SQL.

### Entregáveis

* `entregas/CHECKLIST_JUNIOR.md` — o [checklist](../docs/checklist.md)
  preenchido.
* `entregas/TRANSFORMACOES.md` — a tabela da tarefa 3, os grãos da tarefa 4 e
  a resposta da tarefa 6.
* De 5 a 8 *prints* com legenda ("o que estou provando aqui?").

---

## 🔸 Nível Pleno

**Foco:** modelar sem roteiro. Você recebe o problema e decide o desenho.

### Tarefas

**1. Refaça a etapa 3 só com o modelo.**
Rode `make reset-oltp`. Escreva o DDL inteiro da evolução do transacional em
`entregas/oltp_evolucao.sql`, consultando **apenas** o
`02_oltp_evoluido.dbml` — sem o roteiro da etapa 3 e sem o gabarito. Aplique e
rode `make conferir-oltp` até zerar. Depois compare com o gabarito e anote o
que você fez diferente e por quê.

**2. Regras de domínio.**
Hoje nada impede um pedido com `status = 'banana'`. Crie restrições `CHECK`
para os domínios abaixo e prove que os dados continuam entrando:

| Coluna | Valores válidos |
|---|---|
| `pedidos.status` e `status_pedidos.status` | `criado`, `pago`, `separado`, `enviado`, `entregue`, `cancelado`, `devolvido` |
| `pagamentos.forma` | `pix`, `cartao_credito`, `cartao_debito`, `boleto` |
| `pagamentos.status` | `pendente`, `aprovado`, `recusado`, `expirado`, `estornado` |
| `auditoria_pedidos.motivo_fraude` | `geolocalizacao`, `troca_dispositivo`, `dispositivo_compartilhado` (ou nulo) |
| `produtos.peso_gramas` | maior que zero (ou nulo) |

A prova é o próprio simulador: `make historico args=--limpar` e
`make streaming ciclos=10` precisam continuar rodando até o fim.

**3. Índices.**
As chaves estrangeiras que você criou na etapa 3 não têm índice. Escolha as
três consultas mais lentas da etapa 4 (use `EXPLAIN ANALYZE`), crie os
índices que as ajudam e mostre o plano antes e depois.

**4. Uma fato nova: pagamentos.**
A diretoria financeira quer saber a **taxa de recusa por forma de pagamento**
e o **valor estornado por mês**. Modele `fato_pagamentos`:
defina o grão, as chaves e as medidas; escreva o DDL
(`entregas/fato_pagamentos.sql`) e o passo de ETL
(`entregas/13_fato_pagamentos.sql`), no padrão dos arquivos de `etl/sql/`,
com `MERGE` e com prova no final. Reaproveite `dim_forma_pagamento` e
`dim_tempo`.

**5. Histórico de custo da transportadora.**
`dim_transportadora` é SCD tipo 1. Se a Barato Fretes reajustar o
`custo_por_kg`, o DW esquece o valor antigo. Transforme-a em **SCD tipo 2**:
altere a dimensão, reescreva o passo 05 e ajuste o `JOIN` do passo 10 para
buscar a versão válida na data de saída. Prove alterando o custo no
transacional, rodando o ETL e mostrando as duas versões — com os fretes
antigos ainda ligados ao custo antigo.

**6. Um dashboard a mais.**
Crie o dashboard **Financeiro**, com pelo menos quatro gráficos sobre a
`fato_pagamentos`.

### Evidências mínimas

* `make conferir-oltp` com 0 pendências depois da tarefa 1.
* `make historico` e `make streaming ciclos=10` rodando **com os `CHECK`
  criados**, e um `INSERT` inválido sendo recusado.
* `EXPLAIN ANALYZE` antes e depois de cada índice.
* A prova do seu passo 13: uma consulta que compare a fato com a staging.
* Duas versões de uma transportadora em `dim_transportadora`, com validade.
* `make validar` ainda com **0 falharam** depois de tudo.

### Entregáveis

* Os arquivos `.sql` das tarefas 1, 2, 3, 4 e 5 em `entregas/`.
* `entregas/modelo_pleno.dbml` — o `04_dw_evoluido.dbml` com as suas mudanças.
* `entregas/RELATORIO_PLENO.md` com:
  * o grão e a justificativa da `fato_pagamentos`;
  * o que mudou entre o seu DDL e o gabarito (tarefa 1);
  * 3 riscos da mudança da tarefa 5 e como você os trataria em produção.

---

## 🟣 Nível Sênior

**Foco:** as decisões que não aparecem no diagrama — operação, qualidade,
custo e risco.

### Tarefas

**1. Evolução sem parar a loja.**
Na etapa 3, `pedidos.status` foi criada como `NOT NULL DEFAULT 'criado'` de
uma vez, numa tabela vazia. Escreva o plano para fazer a mesma mudança numa
tabela `pedidos` com **200 milhões de linhas e o site no ar**: a sequência de
comandos, o que cada um bloqueia, como preencher as linhas antigas em lotes e
como validar antes de tornar a coluna obrigatória. Execute o plano aqui (com
os 5 mil pedidos) para provar que a sequência funciona.

**2. Carga incremental de verdade.**
O passo 01 copia **todas** as tabelas a cada execução. Reescreva-o para
extrair só o que mudou desde a última carga, usando `updated_at` e uma tabela
de controle (*watermark*). Responda no relatório: o que acontece com uma
linha **apagada** no transacional? E com uma linha alterada **durante** a
extração?

**3. Reprocessamento.**
Um erro no ETL carregou errado os dados de três dias atrás. Escreva o
procedimento (e os SQLs) para reprocessar **só uma janela de datas** das
quatro fatos, sem duplicar e sem deixar buraco. O que muda para a
`fato_ciclo_pedido`, que é um snapshot acumulado?

**4. Testes de qualidade no pipeline.**
Escreva um conjunto de testes em SQL que rode **entre** as dimensões e as
fatos e **interrompa** a carga se falhar. No mínimo: `sk_` única em cada
dimensão; nenhuma chave de fato órfã; uma versão atual por pessoa; versões
sem sobreposição; nenhuma medida nula. Mostre um teste falhando de propósito.

**5. Uma fato sem medida.**
A dimensão `dim_dispositivo.is_compartilhado` acha os anéis de fraude, mas não
diz **quando** cada conta entrou no anel. Modele `fato_uso_dispositivo`
(pessoa × dispositivo × dia), uma fato **sem medida** (*factless*), e use-a
para responder: "em que data cada anel passou a ter três contas?"

**6. Particionamento.**
Proponha o particionamento de `fato_pedidos` por mês. Implemente, recarregue e
compare o plano de uma consulta de um mês específico antes e depois. Em que
volume isso passaria a valer a pena?

**7. Dado pessoal.**
A coluna `telefone` saiu da fato na etapa 6. O que mais no DW é dado pessoal
(LGPD)? Proponha o que mascarar, o que remover e o que manter, e quem pode ver
o quê.

**8. Deixe pronto para o próximo.**
Exporte o banco do Metabase com os seus dashboards
(`docker exec modelagem_metabase_db pg_dump -U metabase metabase`) e descreva
como um colega subiria o ambiente já com eles. É assim que o backup deste
repositório nasceu.

### Evidências mínimas

* A sequência da tarefa 1 executada, com `make conferir-oltp` e
  `make streaming ciclos=10` passando ao final.
* Duas execuções seguidas do seu passo 01 incremental: a segunda copiando
  zero linhas com o streaming desligado, e poucas com ele ligado.
* Um reprocessamento de janela seguido de `make validar` com 0 falhas.
* A saída dos testes de qualidade, com um caso passando e um falhando.
* A consulta da tarefa 5 com a data de formação de cada um dos 6 anéis.
* `EXPLAIN (ANALYZE, BUFFERS)` antes e depois do particionamento.

### Entregáveis

* Os arquivos `.sql` de cada tarefa em `entregas/`.
* `entregas/RELATORIO_SENIOR.md`, com uma seção por tarefa no formato de um
  registro de decisão:
  * **Contexto** — qual era o problema;
  * **Decisão** — o que você escolheu;
  * **Alternativas** — o que considerou e descartou, e por quê;
  * **Consequências** — o que fica mais fácil e o que fica mais difícil.
* `entregas/metabase_backup.sql` (tarefa 8).

---

## Como saber se ficou bom

Um critério vale para os três níveis: **outra pessoa consegue reproduzir?**
Entregue o comando, a saída e uma frase dizendo o que aquela saída prova. Veja
o [guia de validação por evidências](../docs/validacao_evidencia.md).

---

# 🏁 Fim da trilha

Você evoluiu um modelo transacional, redesenhou um Data Warehouse, escreveu a
transformação entre os dois e mostrou o resultado a quem decide.

Para continuar a Jornada:

* [`jornada_dados`](https://github.com/sudoers-ai/jornada_dados) — o mesmo
  universo com CDC, Kafka, Spark e Delta Lake.
* [`jornada_dados_nosql`](https://github.com/sudoers-ai/jornada_dados_nosql)
  — os cinco paradigmas não relacionais.
* [`integracao/`](../integracao/README.md) — como ligar este repositório aos
  outros dois.
