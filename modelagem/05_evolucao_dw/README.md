# 6️⃣ Evoluir o dimensional

> ⬅️ Anterior: [5. O DW de hoje](../04_dw_legado/README.md) · [README principal](../../README.md) · Etapa 6 de 9

Esta é a etapa central da disciplina. Você vai redesenhar o Data Warehouse
para que ele responda às três demandas — e, no caminho, corrigir os erros que
encontrou na etapa 5.

A ideia para levar daqui é uma só:

> **O dimensional não é uma cópia do transacional.** Cada tabela que você
> criou na etapa 3 vai reaparecer aqui com **outra forma**: algumas se juntam,
> outras se desdobram, colunas viram tabelas, linhas viram colunas, e nascem
> dados que não existiam. O dado é o mesmo. O desenho muda porque a
> **pergunta** muda.

O modelo de referência é o
[`04_dw_evoluido.dbml`](../dbml/04_dw_evoluido.dbml). Cole-o no
[dbdiagram.io/d](https://dbdiagram.io/d) e deixe aberto.

![Dimensional evoluído](../img/04_dw_evoluido.svg "Dimensões em azul (existentes) e verde (novas); fatos novas em roxo")

---

## Seis ideias antes dos comandos

Se alguma parecer abstrata agora, siga em frente: cada uma vai aparecer num
comando concreto. O texto completo está em
[docs/modelagem.md](../../docs/modelagem.md).

**1. Fato e dimensão.** A **fato** guarda o que aconteceu e os números do
acontecimento (vendeu 3 unidades, pesava 2 kg, custou R$ 90). A **dimensão**
guarda o contexto (quem, o quê, onde, quando, como). Fatos são compridas e
estreitas; dimensões são curtas e largas.

**2. Grão.** É a resposta para "o que é **uma linha** desta fato?". Tem que
caber numa frase. Toda medida da fato precisa estar nesse grão — foi o erro
do `total` na etapa 5.

**3. Chave substituta (`sk_`).** Cada dimensão tem uma chave própria, gerada
pelo DW. É ela, e não o `id` do transacional, que liga a fato à dimensão.

**4. Desnormalizar.** No DW, repetir texto é permitido e desejável. O nome da
categoria vai para dentro do produto; a região vai para dentro da UF.

**5. Dimensão que muda devagar (SCD).** Quando um atributo muda, há duas
saídas: **sobrescrever** (tipo 1, o passado é esquecido) ou **criar uma versão
nova com data de validade** (tipo 2, o passado é preservado).

**6. Três tipos de fato.** *Transacional* (uma linha por acontecimento),
*snapshot periódico* (uma linha por período) e *snapshot acumulado* (uma
linha por processo, atualizada a cada marco). Você vai criar os três.

---

## O mapa da transformação

Esta tabela é o resumo da etapa. Volte a ela sempre que se perguntar "de onde
veio isto?".

| No transacional | Vira, no dimensional | O que acontece no caminho |
|---|---|---|
| `pedidos.dt_venda` (uma coluna) | **`dim_tempo`** (uma tabela) | A data ganha mês, trimestre, dia da semana, fim de semana e feriado, calculados uma vez |
| `auditoria_pedidos.uf` (2 letras) | **`dim_localidade`** | A UF ganha nome, região e a regra "é área atendida?" |
| `pessoas` + `enderecos` | **`dim_pessoas`** (SCD tipo 2) | Duas tabelas viram uma. Cada endereço que a pessoa teve vira uma **versão** dela |
| `produtos` + `categorias` | **`dim_produtos`** (SCD tipo 1) | Duas tabelas viram uma. O nome da categoria entra no produto |
| `dispositivos` | **`dim_dispositivo`** | Ganha fabricante e "quantas contas usam este aparelho" — dados que não existem na origem |
| `transportadoras` | **`dim_transportadora`** | Quase uma cópia, com chave substituta |
| `pagamentos.forma` (um texto) | **`dim_forma_pagamento`** | Um atributo vira uma tabela |
| `pedidos` + `itens_pedidos` + `auditoria_pedidos` + `pagamentos` | **`fato_pedidos`** (transacional) | Quatro tabelas viram uma. Grão: item de pedido |
| `transportes` + `carga_pedidos` | **`fato_entregas`** (transacional) | O frete do caminhão é rateado por pedido. Nascem dias de trânsito e de atraso |
| `status_pedidos` (5 linhas por pedido) | **`fato_ciclo_pedido`** (snapshot acumulado) | As linhas "deitam": cada situação vira uma coluna de data |
| — (não existe na origem) | **`fato_peso_diario`** (snapshot periódico) | Um agregado por dia, calculado a partir de outra fato |

Repare na última coluna: em **nenhuma** linha está escrito "copia".

---

## Como trabalhar nesta etapa

Igual à etapa 3, agora no outro banco:

```bash
make psql-dw
```

Cole os blocos no `psql`, na ordem, e use um segundo terminal para conferir.

---

## A sua lista de tarefas

<!-- rodar: shell falha-esperada -->
```bash
make conferir-dw
```

```
❌ Modelagem do DIMENSIONAL (DW) incompleta. Corrija antes de continuar:

   dim_tempo                        a tabela não existe
   dim_localidade                   a tabela não existe
   dim_pessoas.id_endereco          a coluna não existe
   dim_pessoas.cidade               a coluna não existe
   dim_pessoas.uf                   a coluna não existe
   dim_pessoas.dt_inicio            a coluna não existe
   dim_pessoas.dt_fim               a coluna não existe
   dim_pessoas.is_atual             a coluna não existe
   dim_produtos.peso_gramas         a coluna não existe
   dim_dispositivo                  a tabela não existe
   dim_transportadora               a tabela não existe
   dim_forma_pagamento              a tabela não existe
   fato_pedidos.id_produto          a coluna não existe
   fato_pedidos.sk_tempo            a coluna não existe
   fato_pedidos.sk_dispositivo      a coluna não existe
   fato_pedidos.sk_localidade       a coluna não existe
   fato_pedidos.sk_forma_pagamento  a coluna não existe
   fato_pedidos.qtde                deveria ser NOT NULL
   fato_pedidos.valor_unit          deveria ser NOT NULL
   fato_pedidos.valor_total         a coluna não existe
   fato_pedidos.peso_gramas         a coluna não existe
   fato_pedidos.status              a coluna não existe
   fato_pedidos.is_fraude           a coluna não existe
   fato_pedidos.motivo_fraude       a coluna não existe
   fato_pedidos.dispositivo         esta coluna não existe no modelo novo (remova com DROP COLUMN)
   fato_pedidos.telefone            esta coluna não existe no modelo novo (remova com DROP COLUMN)
   fato_pedidos.total               esta coluna não existe no modelo novo (remova com DROP COLUMN)
   fato_pedidos                     falta a chave única (UNIQUE) em (id_pedido, id_produto)
   fato_entregas                    a tabela não existe
   fato_ciclo_pedido                a tabela não existe
   fato_peso_diario                 a tabela não existe

   31 pendência(s). O modelo de referência é modelagem/dbml/04_dw_evoluido.dbml
   ...
   ⚠️  stg_pedidos: tabela que não está no modelo novo (não impede de seguir)
   ⚠️  stg_pessoas: tabela que não está no modelo novo (não impede de seguir)
   ⚠️  stg_produtos: tabela que não está no modelo novo (não impede de seguir)
```

São **31 pendências**. Repare que, diferente do transacional, aqui há colunas
para **remover**. No DW isso é permitido — e você vai ver por quê agora.

---

## 6.1 Esvaziar o legado

<!-- rodar: dw -->
```sql
TRUNCATE fato_pedidos, dim_pessoas, dim_produtos RESTART IDENTITY CASCADE;

DROP TABLE IF EXISTS stg_pessoas, stg_produtos, stg_pedidos;
```

> ⚠️ Este é o **único bloco da etapa que apaga dados**. Se você colá-lo de
> novo mais adiante, depois de carregar o DW, basta rodar `make etl` outra
> vez para reconstruir tudo.

**Como assim, apagar o Data Warehouse?** Na etapa 3 a regra era "acrescente,
não quebre". Aqui a regra é outra, e a diferença entre os dois bancos é esta:

* O **transacional** é a origem. Se você apagar um pedido de lá, ele deixa de
  existir no mundo.
* O **dimensional** é **derivado**. Tudo que está nele foi calculado a partir
  do transacional, e pode ser calculado de novo.

Como o DW antigo está com os números errados (etapa 5), o caminho mais seguro
é esvaziar, redesenhar e **recarregar do zero** com um ETL novo. O
`RESTART IDENTITY` zera os contadores das `sk_`. As tabelas `stg_*` saem
porque o novo ETL usa outra área de staging.

---

## 6.2 Dimensões que não vêm do transacional

Duas dimensões não têm tabela de origem. Elas guardam **conhecimento do
negócio**.

### `dim_tempo` — o calendário

<!-- rodar: dw -->
```sql
CREATE TABLE IF NOT EXISTS dim_tempo (
    sk_tempo       integer PRIMARY KEY,
    data           date NOT NULL UNIQUE,
    ano            integer NOT NULL,
    trimestre      integer NOT NULL,
    mes            integer NOT NULL,
    nome_mes       varchar(20) NOT NULL,
    semana_ano     integer NOT NULL,
    dia            integer NOT NULL,
    dia_semana     integer NOT NULL,
    nome_dia       varchar(20) NOT NULL,
    is_fim_semana  boolean NOT NULL,
    is_feriado     boolean NOT NULL
);
```

| No transacional | Aqui |
|---|---|
| `dt_venda` é uma coluna `timestamp`. Para saber se foi num sábado, alguém escreve `EXTRACT(dow FROM dt_venda) = 6` | Uma linha por **dia**, com tudo sobre ele já calculado. "Vendas em fim de semana" vira `WHERE is_fim_semana` |

O que observar:

* **`sk_tempo` não é `serial`.** É a própria data escrita como número:
  `20261013` é 13/10/2026. É a única chave substituta do DW que tem
  significado, por conveniência: dá para ler e para filtrar por faixa.
* **`is_feriado` não existe em banco transacional nenhum.** É conhecimento
  do negócio que só o DW guarda.
* Toda fato vai apontar para cá. É a dimensão mais reaproveitada de qualquer
  Data Warehouse.

### `dim_localidade` — a UF e a regra de atendimento

<!-- rodar: dw -->
```sql
CREATE TABLE IF NOT EXISTS dim_localidade (
    sk_localidade     serial PRIMARY KEY,
    uf                char(2) NOT NULL UNIQUE,
    nome_uf           varchar(50) NOT NULL,
    regiao            varchar(20) NOT NULL,
    is_area_atendida  boolean NOT NULL
);
```

| No transacional | Aqui |
|---|---|
| `auditoria_pedidos.uf` são duas letras. A regra "só atendemos SP, MG e RJ" estava num `CASE` dentro de um dashboard | A regra vira a coluna `is_area_atendida`. Todo relatório usa a mesma |

Esta é a correção do **problema 3** da etapa 5: a regra de negócio sai do
gráfico e vem morar no modelo.

---

## 6.3 Dimensões que já existiam

### `dim_pessoas` — passa a guardar o passado (SCD tipo 2)

<!-- rodar: dw -->
```sql
ALTER TABLE dim_pessoas
    ADD COLUMN IF NOT EXISTS id_endereco  integer,
    ADD COLUMN IF NOT EXISTS cidade       varchar(100),
    ADD COLUMN IF NOT EXISTS uf           char(2),
    ADD COLUMN IF NOT EXISTS dt_inicio    timestamp NOT NULL,
    ADD COLUMN IF NOT EXISTS dt_fim       timestamp,
    ADD COLUMN IF NOT EXISTS is_atual     boolean NOT NULL DEFAULT true;
```

| No transacional | Aqui |
|---|---|
| `pessoas` e `enderecos` são duas tabelas. A pessoa tem um endereço principal **hoje** | Uma tabela só. Cidade e UF entram na pessoa, e **cada endereço que ela já teve vira uma linha** |

As três últimas colunas são o que transforma uma dimensão comum em SCD tipo 2:

| Coluna | Para quê |
|---|---|
| `dt_inicio` | a partir de quando esta versão vale |
| `dt_fim` | até quando valeu. Nula = ainda vale |
| `is_atual` | atalho para "é a versão de hoje?" |

Lembra do Ravi Rios, que se mudou de Barbosa das Pedras para Souza? Ele terá
**duas linhas** aqui, com o mesmo `id` (7) e duas `sk_pessoa` diferentes. As
compras antigas apontam para a primeira; as novas, para a segunda.

É a correção do **problema 2** da etapa 5. O ETL antigo já criava uma linha
nova quando algo mudava — só faltava dizer **quando cada uma vale**.

> `dt_inicio` pôde ser `NOT NULL` sem `DEFAULT` porque você esvaziou a tabela
> no passo 6.1. Com dado dentro, o banco teria recusado (a regra 2 da etapa 3
> vale em qualquer banco).

### `dim_produtos` — ganha o peso

<!-- rodar: dw -->
```sql
ALTER TABLE dim_produtos
    ADD COLUMN IF NOT EXISTS peso_gramas integer;
```

Esta continua **tipo 1**: quando o produto muda, a linha é sobrescrita.

**Por que o preço não vem para cá?** Porque o preço muda toda semana. Se
ficasse na dimensão, ou você perderia o preço antigo (tipo 1) ou criaria uma
versão do produto a cada reajuste (tipo 2). O que interessa é o preço **no
momento da venda** — e isso é um número do acontecimento. Mora na fato.

---

## 6.4 Dimensões novas

### `dim_dispositivo` — com atributos que não existem na origem

<!-- rodar: dw -->
```sql
CREATE TABLE IF NOT EXISTS dim_dispositivo (
    sk_dispositivo    serial PRIMARY KEY,
    device_id         varchar(20) NOT NULL UNIQUE,
    modelo            varchar(50) NOT NULL,
    sistema           varchar(20) NOT NULL,
    fabricante        varchar(30) NOT NULL,
    qtd_contas        integer NOT NULL DEFAULT 0,
    is_compartilhado  boolean NOT NULL DEFAULT false
);
```

| Coluna | De onde vem |
|---|---|
| `device_id`, `modelo`, `sistema` | tabela `dispositivos` |
| `fabricante` | **calculado**: extraído do texto do modelo ("iPhone 15" → Apple) |
| `qtd_contas` | **calculado**: quantas pessoas diferentes compraram por este aparelho (cruza `auditoria_pedidos` com `pedidos`) |
| `is_compartilhado` | **calculado**: `qtd_contas >= 3` |

Metade das colunas desta dimensão **não existe em lugar nenhum do
transacional**. É isso que "transformar" significa: a consulta de três
tabelas que você escreveu na etapa 4 para achar os anéis de fraude vai rodar
uma vez, dentro do ETL, e o resultado fica guardado como um atributo.

### `dim_transportadora`

<!-- rodar: dw -->
```sql
CREATE TABLE IF NOT EXISTS dim_transportadora (
    sk_transportadora  serial PRIMARY KEY,
    id                 integer NOT NULL UNIQUE,
    nome               varchar(100) NOT NULL,
    cnpj               varchar(18) NOT NULL,
    custo_por_kg       numeric(10,2) NOT NULL
);
```

A mais parecida com a origem. Mesmo assim tem a sua `sk_transportadora`, e o
`id` do transacional fica como um atributo comum (a "chave de negócio").

### `dim_forma_pagamento` — um atributo vira tabela

<!-- rodar: dw -->
```sql
CREATE TABLE IF NOT EXISTS dim_forma_pagamento (
    sk_forma_pagamento  serial PRIMARY KEY,
    forma               varchar(20) NOT NULL UNIQUE,
    descricao           varchar(50) NOT NULL,
    is_a_vista          boolean NOT NULL
);
```

| No transacional | Aqui |
|---|---|
| `pagamentos.forma` é um texto (`'cartao_credito'`). Não existe tabela "formas de pagamento" | Vira uma dimensão, com um nome apresentável e um atributo novo |

Regra prática: **tudo pelo que você quer agrupar ou filtrar é candidato a
dimensão**, mesmo que no transacional seja só uma coluna de texto.

## ✔️ Confira as dimensões

<!-- rodar: shell falha-esperada -->
```bash
make conferir-dw
```

```
❌ Modelagem do DIMENSIONAL (DW) incompleta. Corrija antes de continuar:

   fato_pedidos.id_produto          a coluna não existe
   fato_pedidos.sk_tempo            a coluna não existe
   fato_pedidos.sk_dispositivo      a coluna não existe
   fato_pedidos.sk_localidade       a coluna não existe
   fato_pedidos.sk_forma_pagamento  a coluna não existe
   fato_pedidos.qtde                deveria ser NOT NULL
   fato_pedidos.valor_unit          deveria ser NOT NULL
   fato_pedidos.valor_total         a coluna não existe
   fato_pedidos.peso_gramas         a coluna não existe
   fato_pedidos.status              a coluna não existe
   fato_pedidos.is_fraude           a coluna não existe
   fato_pedidos.motivo_fraude       a coluna não existe
   fato_pedidos.dispositivo         esta coluna não existe no modelo novo (remova com DROP COLUMN)
   fato_pedidos.telefone            esta coluna não existe no modelo novo (remova com DROP COLUMN)
   fato_pedidos.total               esta coluna não existe no modelo novo (remova com DROP COLUMN)
   fato_pedidos                     falta a chave única (UNIQUE) em (id_pedido, id_produto)
   fato_entregas                    a tabela não existe
   fato_ciclo_pedido                a tabela não existe
   fato_peso_diario                 a tabela não existe

   19 pendência(s). O modelo de referência é modelagem/dbml/04_dw_evoluido.dbml
```

De 31 para **19**.

As 7 dimensões estão prontas. O que resta são as fatos.

---

## 6.5 A fato que já existia: `fato_pedidos`

**Grão: uma linha por item de pedido.**

<!-- rodar: dw -->
```sql
ALTER TABLE fato_pedidos
    DROP COLUMN IF EXISTS dispositivo,
    DROP COLUMN IF EXISTS telefone,
    DROP COLUMN IF EXISTS total,
    ADD COLUMN IF NOT EXISTS id_produto          integer NOT NULL,
    ADD COLUMN IF NOT EXISTS sk_tempo            integer NOT NULL REFERENCES dim_tempo (sk_tempo),
    ADD COLUMN IF NOT EXISTS sk_dispositivo      integer NOT NULL REFERENCES dim_dispositivo (sk_dispositivo),
    ADD COLUMN IF NOT EXISTS sk_localidade       integer NOT NULL REFERENCES dim_localidade (sk_localidade),
    ADD COLUMN IF NOT EXISTS sk_forma_pagamento  integer NOT NULL REFERENCES dim_forma_pagamento (sk_forma_pagamento),
    ADD COLUMN IF NOT EXISTS valor_total         numeric(10,2) NOT NULL,
    ADD COLUMN IF NOT EXISTS peso_gramas         integer NOT NULL,
    ADD COLUMN IF NOT EXISTS status              varchar(20) NOT NULL,
    ADD COLUMN IF NOT EXISTS is_fraude           boolean NOT NULL,
    ADD COLUMN IF NOT EXISTS motivo_fraude       varchar(30),
    ALTER COLUMN qtde SET NOT NULL,
    ALTER COLUMN valor_unit SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_fato_pedidos_item
    ON fato_pedidos (id_pedido, id_produto);
```

É o comando mais longo da etapa. Leia em três partes.

**O que sai (`DROP COLUMN`):**

| Coluna | Por que sai |
|---|---|
| `total` | O valor do pedido inteiro numa fato de itens: grão errado. É o **problema 1** da etapa 5 |
| `dispositivo` | O texto do modelo. Agora existe `dim_dispositivo`; a fato guarda só a `sk_dispositivo` |
| `telefone` | Dado pessoal que nenhuma análise usa. DW não é lugar de guardar o que não se analisa |

**O que entra (`ADD COLUMN`):**

| Coluna | Tipo | O que é |
|---|---|---|
| `sk_tempo`, `sk_dispositivo`, `sk_localidade`, `sk_forma_pagamento` | chaves | As ligações com as dimensões novas. Cada uma é uma chave estrangeira |
| `valor_total` | **medida** | O valor do **item**. Substitui `total` — e este pode ser somado |
| `peso_gramas` | **medida** | O peso do item (quantidade × peso do produto). Não existe no transacional: nasce no ETL |
| `status` | atributo | A situação atual do pedido |
| `is_fraude`, `motivo_fraude` | atributos | O resultado da análise antifraude |
| `id_produto` | chave de negócio | Com `id_pedido`, identifica a linha |

**O que aperta:**

* `qtde` e `valor_unit` viram `NOT NULL`. Medida nula numa fato é uma
  armadilha: `SUM` ignora o nulo em silêncio, e `COUNT` passa a discordar de
  `COUNT(*)`.
* O índice único em (`id_pedido`, `id_produto`) é o grão **escrito como
  regra**: o banco passa a recusar duas linhas para o mesmo item do mesmo
  pedido. O problema 2 da etapa 5 (vendas duplicadas) deixa de ser possível.

> Uma fato é feita de dois tipos de coluna: **chaves** (as `sk_`, que apontam
> para as dimensões) e **medidas** (os números que se somam). Quando sobra
> texto descritivo numa fato, quase sempre ele deveria estar numa dimensão.

---

## 6.6 Fato nova: `fato_entregas`

**Grão: uma linha por pedido embarcado em um transporte.**

<!-- rodar: dw -->
```sql
CREATE TABLE IF NOT EXISTS fato_entregas (
    sk_id                serial PRIMARY KEY,
    id_transporte        integer NOT NULL,
    id_pedido            integer NOT NULL,
    sk_transportadora    integer NOT NULL REFERENCES dim_transportadora (sk_transportadora),
    sk_pessoa            bigint  NOT NULL REFERENCES dim_pessoas (sk_pessoa),
    sk_localidade        integer NOT NULL REFERENCES dim_localidade (sk_localidade),
    sk_tempo_saida       integer NOT NULL REFERENCES dim_tempo (sk_tempo),
    sk_tempo_entrega     integer REFERENCES dim_tempo (sk_tempo),
    dt_saida             timestamp NOT NULL,
    dt_entrega_prevista  timestamp NOT NULL,
    dt_entrega           timestamp,
    peso_gramas          integer NOT NULL,
    valor_frete          numeric(10,2) NOT NULL,
    dias_transito        integer,
    dias_atraso          integer,
    is_entregue          boolean NOT NULL,
    is_atrasada          boolean NOT NULL,
    UNIQUE (id_transporte, id_pedido)
);
```

**Por que uma fato separada, e não mais colunas em `fato_pedidos`?** Porque o
grão é outro. `fato_pedidos` tem uma linha por **item**; a entrega acontece
por **pedido**. Colocar o frete na fato de itens seria repetir o erro do
`total`. Regra: **processo de negócio diferente, grão diferente, fato
diferente.**

O que observar:

* **`sk_tempo_saida` e `sk_tempo_entrega` apontam para a mesma `dim_tempo`.**
  Uma dimensão, dois papéis. Não se cria uma "dim_tempo_entrega".
* **`sk_tempo_entrega` aceita nulo**: enquanto o caminhão está na estrada,
  não há data de entrega.
* **`valor_frete` é um rateio.** No transacional o frete é do caminhão
  (`transportes.valor_frete`). Aqui o grão é o pedido, então o valor é
  distribuído pelo peso de cada um.
* **`dias_transito`, `dias_atraso` e `is_atrasada` não existem no
  transacional.** São medidas calculadas no ETL, uma vez, com uma regra só.

---

## 6.7 Fato nova: `fato_ciclo_pedido`

**Grão: uma linha por pedido, atualizada a cada marco do ciclo.**

<!-- rodar: dw -->
```sql
CREATE TABLE IF NOT EXISTS fato_ciclo_pedido (
    id_pedido            integer PRIMARY KEY,
    sk_pessoa            bigint  NOT NULL REFERENCES dim_pessoas (sk_pessoa),
    sk_tempo_criado      integer NOT NULL REFERENCES dim_tempo (sk_tempo),
    status_atual         varchar(20) NOT NULL,
    dt_criado            timestamp NOT NULL,
    dt_pago              timestamp,
    dt_separado          timestamp,
    dt_enviado           timestamp,
    dt_entregue          timestamp,
    dt_cancelado         timestamp,
    dt_devolvido         timestamp,
    horas_ate_pagamento  numeric(10,2),
    horas_ate_envio      numeric(10,2),
    horas_ate_entrega    numeric(10,2),
    valor_total          numeric(10,2) NOT NULL,
    is_fraude            boolean NOT NULL
);
```

Esta é a transformação mais radical da disciplina. Compare:

```text
NO TRANSACIONAL (status_pedidos)            NO DIMENSIONAL (fato_ciclo_pedido)
uma linha por EVENTO                        uma linha por PEDIDO

 id_pedido | status   | dt_evento           id_pedido | dt_criado | dt_pago | dt_separado | dt_enviado | dt_entregue
 ----------+----------+-----------          ----------+-----------+---------+-------------+------------+------------
        1  | criado   | 13/09 10:38                1  | 13/09     | 15/09   | 16/09       | 16/09      | 17/09
        1  | pago     | 15/09 19:54
        1  | separado | 16/09 01:44
        1  | enviado  | 16/09 15:30
        1  | entregue | 17/09 20:10
```

As linhas "deitam". Cada situação vira uma **coluna de data**. "Quanto tempo
do pagamento ao envio?" deixa de ser a tabela juntada com ela mesma e vira
uma subtração entre duas colunas.

O que observar:

* **Quase todas as datas aceitam nulo.** A linha nasce com `dt_criado` e vai
  sendo **preenchida** conforme o pedido anda. É a única fato em que `UPDATE`
  é a rotina, e por isso se chama *snapshot acumulado*.
* **A chave primária é o próprio `id_pedido`**: uma linha por pedido, sempre.
* **`horas_ate_...`** são os tempos entre os marcos, já calculados.

---

## 6.8 Fato nova: `fato_peso_diario`

**Grão: uma linha por dia e transportadora.**

<!-- rodar: dw -->
```sql
CREATE TABLE IF NOT EXISTS fato_peso_diario (
    sk_tempo           integer NOT NULL REFERENCES dim_tempo (sk_tempo),
    sk_transportadora  integer NOT NULL REFERENCES dim_transportadora (sk_transportadora),
    qtd_transportes    integer NOT NULL,
    qtd_pedidos        integer NOT NULL,
    peso_total_gramas  bigint NOT NULL,
    valor_frete_total  numeric(12,2) NOT NULL,
    PRIMARY KEY (sk_tempo, sk_transportadora)
);
```

É a resposta literal da Demanda 2 ("quero o histórico diário do peso
transportado"). Em vez de recalcular sobre milhares de entregas a cada vez
que alguém abre o dashboard, o número fica pronto: é um *snapshot periódico*.

O que observar:

* **Não tem `sk_id`.** A chave primária é o próprio grão: o par (dia,
  transportadora).
* **Não existe coluna de média.** A diretoria pediu "peso médio por pedido",
  mas a fato guarda o **peso total** e a **quantidade de pedidos**. Média não
  se soma: a média de duas médias não é a média do todo. Guarde os
  ingredientes e divida na hora da consulta.
* **`bigint` no peso**: somas de gramas ultrapassam o limite de um `integer`
  com facilidade.

## ✔️ Confira o dimensional

<!-- rodar: shell -->
```bash
make conferir-dw
```

```
✅ Modelagem do DIMENSIONAL (DW) conferida: 11 tabelas, 110 colunas, 15 FKs, 0 pendências.
```

---

## Veja o que você construiu

<!-- rodar: dw -->
```sql
\dt
```

```
               List of relations
 Schema |        Name         | Type  |  Owner
--------+---------------------+-------+---------
 public | dim_dispositivo     | table | sudoers
 public | dim_forma_pagamento | table | sudoers
 public | dim_localidade      | table | sudoers
 public | dim_pessoas         | table | sudoers
 public | dim_produtos        | table | sudoers
 public | dim_tempo           | table | sudoers
 public | dim_transportadora  | table | sudoers
 public | fato_ciclo_pedido   | table | sudoers
 public | fato_entregas       | table | sudoers
 public | fato_pedidos        | table | sudoers
 public | fato_peso_diario    | table | sudoers
(11 rows)
```

7 dimensões e 4 fatos. Todas vazias: o desenho está pronto, falta o dado.

```
                    dim_tempo        dim_localidade
                        │                  │
   dim_produtos ────────┼──────────────────┼──────── dim_dispositivo
                        │                  │
   dim_pessoas ─────  fato_pedidos   fato_entregas ───── dim_transportadora
        │                                  │
        └──── fato_ciclo_pedido      fato_peso_diario
                                                      dim_forma_pagamento
```

Repare que `dim_tempo`, `dim_pessoas` e `dim_localidade` são usadas por mais
de uma fato. Dimensão compartilhada é o que permite cruzar processos
diferentes ("as entregas atrasadas são dos mesmos clientes que cancelam?").

Saia do `psql` com `\q`.

---

## 🆘 Se algo deu errado

| O que apareceu | O que é | O que fazer |
|---|---|---|
| `ERROR: column "dt_inicio" of relation "dim_pessoas" contains null values` | A tabela não estava vazia quando você criou a coluna `NOT NULL` | Rode o bloco 6.1 (esvaziar) e depois o 6.3 de novo |
| `ERROR: relation "dim_tempo" does not exist` (ao alterar a fato) | A fato aponta para dimensões que ainda não existem | Volte e rode 6.2, 6.3 e 6.4 antes da 6.5 |
| `ERROR: cannot truncate a table referenced in a foreign key constraint` | Faltou o `CASCADE` no fim do `TRUNCATE` | Cole o bloco 6.1 inteiro |
| A conferência aponta coluna "que não existe no modelo novo" | Ficou uma coluna do legado para trás | `ALTER TABLE tabela DROP COLUMN coluna;` |
| Bagunçou tudo e quer recomeçar | — | `make reset-dw` volta o DW ao legado (vazio) |
| Quer ver a resposta pronta | — | `make gabarito-dw`. O arquivo é [`ddl/gabarito/dw_evolucao.sql`](../ddl/gabarito/dw_evolucao.sql) |

Mais em [docs/faq.md](../../docs/faq.md).

---

## ✅ Antes de seguir

* [ ] `make conferir-dw` mostra **0 pendências**
* [ ] `\dt` lista 7 dimensões e 4 fatos
* [ ] Sei dizer, em uma frase, o **grão** de cada uma das 4 fatos
* [ ] Sei por que o preço fica na fato e a categoria fica na dimensão
* [ ] Sei o que `dt_inicio`, `dt_fim` e `is_atual` resolvem
* [ ] Sei por que `fato_peso_diario` não tem coluna de média

---

# ➡️ Continue em [etl/README.md](../../etl/README.md)
