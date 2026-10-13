# 3️⃣ Evoluir o transacional

> ⬅️ Anterior: [2. As três demandas](../02_demandas/README.md) · [README principal](../../README.md) · Etapa 3 de 9

Agora é com você. Nesta etapa você aplica no banco transacional o modelo que
estudou: **7 tabelas novas e 8 colunas novas**.

O modelo de referência é o
[`02_oltp_evoluido.dbml`](../dbml/02_oltp_evoluido.dbml). Para cada mudança,
este roteiro mostra o trecho do modelo, explica as decisões e mostra o comando
SQL. **Leia o comando antes de colar**: o objetivo não é digitar, é entender
por que cada palavra está ali.

---

## Como trabalhar nesta etapa

**1. Abra o `psql` do transacional e deixe aberto:**

```bash
make psql-oltp
```

**2. Abra um segundo terminal**, na pasta do repositório. É nele que você vai
rodar a conferência depois de cada demanda.

**3. Cole os blocos SQL no `psql`**, um de cada vez, na ordem.

> Todos os comandos desta etapa podem ser colados **mais de uma vez** sem
> estragar nada (`IF NOT EXISTS`, `OR REPLACE`). Se você se perdeu, cole de
> novo. E nenhum deles apaga dado.

---

## A sua lista de tarefas

No segundo terminal, peça a conferência:

<!-- rodar: shell falha-esperada -->
```bash
make conferir-oltp
```

Ela compara o seu banco com o modelo e lista o que falta:

```
❌ Modelagem do TRANSACIONAL (OLTP) incompleta. Corrija antes de continuar:

   produtos.peso_gramas             a coluna não existe
   pedidos.id_endereco_entrega      a coluna não existe
   pedidos.status                   a coluna não existe
   auditoria_pedidos.device_id      a coluna não existe
   auditoria_pedidos.uf             a coluna não existe
   auditoria_pedidos.is_fraude      a coluna não existe
   auditoria_pedidos.motivo_fraude  a coluna não existe
   auditoria_pedidos.dt_fraude      a coluna não existe
   dispositivos                     a tabela não existe
   enderecos                        a tabela não existe
   transportadoras                  a tabela não existe
   transportes                      a tabela não existe
   carga_pedidos                    a tabela não existe
   status_pedidos                   a tabela não existe
   pagamentos                       a tabela não existe

   15 pendência(s). O modelo de referência é modelagem/dbml/02_oltp_evoluido.dbml
```

São **15 pendências**: 8 colunas e 7 tabelas. Ao fim desta etapa a lista
precisa estar vazia. Rode `make conferir-oltp` sempre que quiser saber quanto
falta — ela não altera nada.

---

## Quatro regras antes de começar

Elas explicam quase tudo que você vai ver nos comandos.

**Regra 1 — Acrescente, não quebre.** Há sistemas lendo estas tabelas. Você
só **adiciona**: nenhuma coluna existente muda de nome, de tipo ou some.

**Regra 2 — Coluna nova em tabela com dado nasce nula ou com valor padrão.**
Imagine a tabela `produtos` com 200 linhas. Se você criar `peso_gramas` como
`NOT NULL`, o banco pergunta: "e o que eu coloco nas 200 linhas que já
existem?" — e recusa. Só há duas saídas: deixar a coluna aceitar nulo, ou dar
um `DEFAULT`.

**Regra 3 — A ordem importa.** Uma chave estrangeira aponta para uma tabela
que **já precisa existir**. Por isso `dispositivos` nasce antes da coluna
`auditoria_pedidos.device_id`, que aponta para ela.

**Regra 4 — Toda tabela nova ganha o trigger de `updated_at`.** As 6 tabelas
antigas já têm (você viu na etapa 1). É ele que carimba a hora de cada
`UPDATE`, e é desse carimbo que um ETL depende. A função
`update_updated_at_column()` já existe no banco; você só precisa ligá-la a
cada tabela nova.

---

# Demanda 1 — Antifraude

## 1.1 Tabela `dispositivos`

O modelo pede:

```
Table dispositivos {
  device_id varchar(20) [pk]
  modelo varchar(50) [not null]
  sistema varchar(20) [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}
```

Traduzindo linha a linha com o dicionário da etapa 2:

<!-- rodar: oltp -->
```sql
CREATE TABLE IF NOT EXISTS dispositivos (
    device_id   varchar(20) PRIMARY KEY,
    modelo      varchar(50) NOT NULL,
    sistema     varchar(20) NOT NULL,
    created_at  timestamp DEFAULT now(),
    updated_at  timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_dispositivos
    BEFORE UPDATE ON dispositivos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

O que observar:

* **A chave primária é um texto** (`device_id`), não um número gerado pelo
  banco. O identificador do aparelho já existe no mundo real — é a
  "impressão digital" que o site coleta. Quando a entidade já tem um
  identificador natural e estável, ele pode ser a chave.
* **`created_at` e `updated_at`** seguem o padrão das tabelas antigas.
* **O trigger** é a regra 4. `BEFORE UPDATE ... FOR EACH ROW` quer dizer:
  "antes de gravar cada linha alterada, rode a função" — e a função troca o
  `updated_at` pela hora atual.

## 1.2 Colunas novas em `auditoria_pedidos`

O modelo pede (só as linhas marcadas como NOVO):

```
  device_id varchar(20)
  uf char(2)
  is_fraude boolean [not null, default: false]
  motivo_fraude varchar(30)
  dt_fraude timestamp

Ref: auditoria_pedidos.device_id > dispositivos.device_id
```

<!-- rodar: oltp -->
```sql
ALTER TABLE auditoria_pedidos
    ADD COLUMN IF NOT EXISTS device_id      varchar(20) REFERENCES dispositivos (device_id),
    ADD COLUMN IF NOT EXISTS uf             char(2),
    ADD COLUMN IF NOT EXISTS is_fraude      boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS motivo_fraude  varchar(30),
    ADD COLUMN IF NOT EXISTS dt_fraude      timestamp;
```

O que observar:

* **`REFERENCES dispositivos (device_id)`** é a chave estrangeira (o `Ref:`
  do modelo). A partir de agora o banco **recusa** uma auditoria que aponte
  para um aparelho que não existe. A coluna antiga `dispositivo` (o texto)
  continua lá: regra 1.
* **`is_fraude` é a única `NOT NULL`**, e só pode ser porque tem
  `DEFAULT false` (regra 2). Faz sentido para o negócio: todo pedido nasce
  "não é fraude" até alguém provar o contrário.
* **`motivo_fraude` e `dt_fraude` aceitam nulo de propósito.** Para a
  enorme maioria dos pedidos esses campos nunca serão preenchidos. Nulo aqui
  significa "não se aplica", e essa é uma informação legítima.
* **`uf` é `char(2)`**: sempre exatamente duas letras.

## ✔️ Confira a Demanda 1

No segundo terminal:

<!-- rodar: shell falha-esperada -->
```bash
make conferir-oltp
```

```
❌ Modelagem do TRANSACIONAL (OLTP) incompleta. Corrija antes de continuar:

   produtos.peso_gramas         a coluna não existe
   pedidos.id_endereco_entrega  a coluna não existe
   pedidos.status               a coluna não existe
   enderecos                    a tabela não existe
   transportadoras              a tabela não existe
   transportes                  a tabela não existe
   carga_pedidos                a tabela não existe
   status_pedidos               a tabela não existe
   pagamentos                   a tabela não existe

   9 pendência(s). O modelo de referência é modelagem/dbml/02_oltp_evoluido.dbml
```

Saíram 6 linhas da lista (5 colunas e 1 tabela). Restam **9**.

---

# Demanda 2 — Logística e custo de frete

## 2.1 O peso do produto

```
  peso_gramas integer
```

<!-- rodar: oltp -->
```sql
ALTER TABLE produtos
    ADD COLUMN IF NOT EXISTS peso_gramas integer;
```

A menor mudança da etapa, e a regra 2 em estado puro: `produtos` tem 200
linhas, então a coluna nasce aceitando nulo. Neste momento os 200 produtos
estão com peso nulo. Quem preenche é o script da etapa 4.

> **Por que gramas, em número inteiro, e não quilos com vírgula?** Inteiro não
> tem erro de arredondamento, e o frete é somado milhares de vezes. Guarde a
> menor unidade que o negócio usa e converta na hora de exibir.

## 2.2 Tabela `enderecos`

```
Table enderecos {
  id integer [pk, increment]
  id_pessoa bigint [not null]
  logradouro varchar(255) [not null]
  cidade varchar(100) [not null]
  uf char(2) [not null]
  cep varchar(9) [not null]
  is_principal boolean [not null, default: true]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Ref: enderecos.id_pessoa > pessoas.id
```

<!-- rodar: oltp -->
```sql
CREATE TABLE IF NOT EXISTS enderecos (
    id            serial PRIMARY KEY,
    id_pessoa     bigint NOT NULL REFERENCES pessoas (id),
    logradouro    varchar(255) NOT NULL,
    cidade        varchar(100) NOT NULL,
    uf            char(2) NOT NULL,
    cep           varchar(9) NOT NULL,
    is_principal  boolean NOT NULL DEFAULT true,
    created_at    timestamp DEFAULT now(),
    updated_at    timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_enderecos
    BEFORE UPDATE ON enderecos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

O que observar:

* **`id serial`** é o `[pk, increment]` do modelo: o banco gera 1, 2, 3...
  Diferente de `dispositivos`, endereço não tem identificador natural.
* **`id_pessoa bigint`** tem que ter o **mesmo tipo** de `pessoas.id`, que é
  `bigint`. Chave estrangeira e chave referenciada sempre com o mesmo tipo.
* **`id_pessoa` é `NOT NULL`**: não existe endereço sem dono. Aqui pode,
  porque a tabela é nova e está vazia.
* **`is_principal`** é o que permite a pessoa se mudar sem perder o passado:
  o endereço antigo vira `false`, o novo entra como `true`.

## 2.3 O pedido passa a saber para onde vai

```
  id_endereco_entrega integer

Ref: pedidos.id_endereco_entrega > enderecos.id
```

<!-- rodar: oltp -->
```sql
ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS id_endereco_entrega integer REFERENCES enderecos (id);
```

Regra 3 em ação: este comando só funciona porque `enderecos` foi criada no
passo anterior. E a coluna aceita nulo (regra 2): numa empresa real, os
pedidos antigos não teriam essa informação.

## 2.4 Tabela `transportadoras`

```
Table transportadoras {
  id integer [pk, increment]
  nome varchar(100) [not null]
  cnpj varchar(18) [not null, unique]
  custo_por_kg numeric(10,2) [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}
```

<!-- rodar: oltp -->
```sql
CREATE TABLE IF NOT EXISTS transportadoras (
    id            serial PRIMARY KEY,
    nome          varchar(100) NOT NULL,
    cnpj          varchar(18) NOT NULL UNIQUE,
    custo_por_kg  numeric(10,2) NOT NULL,
    created_at    timestamp DEFAULT now(),
    updated_at    timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_transportadoras
    BEFORE UPDATE ON transportadoras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

O que observar:

* **`cnpj ... UNIQUE`**: a chave primária é o `id`, mas o negócio tem outra
  regra — não pode haver duas transportadoras com o mesmo CNPJ. `UNIQUE`
  transforma essa regra em garantia do banco.
* **`numeric(10,2)`** para dinheiro: até 10 dígitos, 2 depois da vírgula,
  **exato**. Nunca use `float` ou `real` para dinheiro: eles arredondam.

## 2.5 Tabela `transportes`

Um transporte é **um caminhão em uma viagem**.

```
Table transportes {
  id integer [pk, increment]
  id_transportadora integer [not null]
  placa varchar(8) [not null]
  peso_total_gramas integer [not null, default: 0]
  valor_frete numeric(10,2) [not null, default: 0]
  dt_saida timestamp [not null]
  dt_entrega_prevista timestamp [not null]
  dt_entrega timestamp
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Ref: transportes.id_transportadora > transportadoras.id
```

<!-- rodar: oltp -->
```sql
CREATE TABLE IF NOT EXISTS transportes (
    id                   serial PRIMARY KEY,
    id_transportadora    integer NOT NULL REFERENCES transportadoras (id),
    placa                varchar(8) NOT NULL,
    peso_total_gramas    integer NOT NULL DEFAULT 0,
    valor_frete          numeric(10,2) NOT NULL DEFAULT 0,
    dt_saida             timestamp NOT NULL,
    dt_entrega_prevista  timestamp NOT NULL,
    dt_entrega           timestamp,
    created_at           timestamp DEFAULT now(),
    updated_at           timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_transportes
    BEFORE UPDATE ON transportes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

O que observar:

* **Três datas, três significados.** `dt_saida` e `dt_entrega_prevista` são
  conhecidas quando o caminhão parte: `NOT NULL`. `dt_entrega` só existe
  quando ele chega: **aceita nulo**. Enquanto está nula, o caminhão está na
  estrada.
* Isso significa que esta linha **nasce incompleta e é completada depois**,
  por um `UPDATE`. Guarde isso: na etapa 7 vai fazer toda a diferença.

## 2.6 Tabela `carga_pedidos` (a relação N:N)

```
Table carga_pedidos {
  id_transporte integer [not null]
  id_pedido integer [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]

  indexes {
    (id_transporte, id_pedido) [pk]
  }
}

Ref: carga_pedidos.id_transporte > transportes.id
Ref: carga_pedidos.id_pedido > pedidos.id
```

<!-- rodar: oltp -->
```sql
CREATE TABLE IF NOT EXISTS carga_pedidos (
    id_transporte  integer NOT NULL REFERENCES transportes (id),
    id_pedido      integer NOT NULL REFERENCES pedidos (id),
    created_at     timestamp DEFAULT now(),
    updated_at     timestamp DEFAULT now(),
    PRIMARY KEY (id_transporte, id_pedido)
);

CREATE OR REPLACE TRIGGER set_updated_at_carga_pedidos
    BEFORE UPDATE ON carga_pedidos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

O que observar:

* **Não existe coluna `id` própria.** A tabela só tem as duas chaves
  estrangeiras. É assim que se reconhece uma tabela associativa.
* **`PRIMARY KEY (id_transporte, id_pedido)`** é uma chave **composta**: o
  que não pode repetir é o **par**. O mesmo pedido não entra duas vezes no
  mesmo caminhão, mas o caminhão leva muitos pedidos.
* Quando a chave tem mais de uma coluna, ela é declarada no fim da tabela,
  e não ao lado de uma coluna.

## ✔️ Confira a Demanda 2

<!-- rodar: shell falha-esperada -->
```bash
make conferir-oltp
```

```
❌ Modelagem do TRANSACIONAL (OLTP) incompleta. Corrija antes de continuar:

   pedidos.status  a coluna não existe
   status_pedidos  a tabela não existe
   pagamentos      a tabela não existe

   3 pendência(s). O modelo de referência é modelagem/dbml/02_oltp_evoluido.dbml
```

Restam **3**: tudo da Demanda 3.

---

# Demanda 3 — Ciclo de vida do pedido

## 3.1 A situação atual do pedido

```
  status varchar(20) [not null, default: 'criado']
```

<!-- rodar: oltp -->
```sql
ALTER TABLE pedidos
    ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'criado';
```

Regra 2 de novo, na versão com `DEFAULT`: a coluna é `NOT NULL` porque todo
pedido **tem** uma situação, e o `DEFAULT 'criado'` diz ao banco o que
colocar nas linhas que já existissem.

## 3.2 Tabela `status_pedidos` (o histórico)

```
Table status_pedidos {
  id_pedido integer [not null]
  status varchar(20) [not null]
  dt_evento timestamp [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]

  indexes {
    (id_pedido, status) [pk]
  }
}

Ref: status_pedidos.id_pedido > pedidos.id
```

<!-- rodar: oltp -->
```sql
CREATE TABLE IF NOT EXISTS status_pedidos (
    id_pedido   integer NOT NULL REFERENCES pedidos (id),
    status      varchar(20) NOT NULL,
    dt_evento   timestamp NOT NULL,
    created_at  timestamp DEFAULT now(),
    updated_at  timestamp DEFAULT now(),
    PRIMARY KEY (id_pedido, status)
);

CREATE OR REPLACE TRIGGER set_updated_at_status_pedidos
    BEFORE UPDATE ON status_pedidos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

O que observar:

* **Uma linha por evento.** Um pedido entregue tem cinco linhas aqui:
  `criado`, `pago`, `separado`, `enviado`, `entregue`, cada uma com a sua
  data. É uma tabela "em pé": cresce para baixo.
* **A chave composta (`id_pedido`, `status`)** garante que um pedido passa
  por cada situação **uma vez só**. A chave primária também serve para
  escrever regra de negócio.

## 3.3 Tabela `pagamentos`

```
Table pagamentos {
  id integer [pk, increment]
  id_pedido integer [not null]
  forma varchar(20) [not null]
  parcelas integer [not null, default: 1]
  valor numeric(10,2) [not null]
  status varchar(20) [not null, default: 'pendente']
  dt_pagamento timestamp
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

Ref: pagamentos.id_pedido > pedidos.id
```

<!-- rodar: oltp -->
```sql
CREATE TABLE IF NOT EXISTS pagamentos (
    id            serial PRIMARY KEY,
    id_pedido     integer NOT NULL REFERENCES pedidos (id),
    forma         varchar(20) NOT NULL,
    parcelas      integer NOT NULL DEFAULT 1,
    valor         numeric(10,2) NOT NULL,
    status        varchar(20) NOT NULL DEFAULT 'pendente',
    dt_pagamento  timestamp,
    created_at    timestamp DEFAULT now(),
    updated_at    timestamp DEFAULT now()
);

CREATE OR REPLACE TRIGGER set_updated_at_pagamentos
    BEFORE UPDATE ON pagamentos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

O que observar:

* **Por que não colocar `forma` e `parcelas` direto em `pedidos`?** Porque
  pagamento tem vida própria: pode ser recusado, tentado de novo, estornado.
  Um pedido, vários pagamentos possíveis. Outra relação um para muitos, outra
  tabela.
* **`dt_pagamento` aceita nulo** pelo mesmo motivo de `dt_entrega`: um boleto
  fica pendente por dias. A linha nasce incompleta.

## ✔️ Confira a Demanda 3

<!-- rodar: shell -->
```bash
make conferir-oltp
```

```
✅ Modelagem do TRANSACIONAL (OLTP) conferida: 13 tabelas, 90 colunas, 13 FKs, 0 pendências.
```

**Lista vazia.** O seu banco transacional está igual ao modelo.

---

## Veja o que você construiu

No `psql`:

<!-- rodar: oltp -->
```sql
\dt
```

```
              List of relations
 Schema |       Name        | Type  |  Owner
--------+-------------------+-------+---------
 public | auditoria_pedidos | table | sudoers
 public | carga_pedidos     | table | sudoers
 public | categorias        | table | sudoers
 public | dispositivos      | table | sudoers
 public | enderecos         | table | sudoers
 public | itens_pedidos     | table | sudoers
 public | pagamentos        | table | sudoers
 public | pedidos           | table | sudoers
 public | pessoas           | table | sudoers
 public | produtos          | table | sudoers
 public | status_pedidos    | table | sudoers
 public | transportadoras   | table | sudoers
 public | transportes       | table | sudoers
(13 rows)
```

De 6 para 13 tabelas, sem tocar em nenhuma coluna que já existia.

### Experimente: o banco agora se defende

Tente registrar o status de um pedido que não existe:

<!-- rodar: oltp falha-esperada -->
```sql
INSERT INTO status_pedidos (id_pedido, status, dt_evento)
VALUES (999999, 'pago', now());
```

```
ERROR:  insert or update on table "status_pedidos" violates foreign key constraint "status_pedidos_id_pedido_fkey"
DETAIL:  Key (id_pedido)=(999999) is not present in table "pedidos".
```

Esse erro é uma **boa notícia**. É a chave estrangeira trabalhando: o banco
se recusa a guardar um dado que não faz sentido. Integridade garantida pelo
banco vale mais do que integridade "que a aplicação cuida".

Saia do `psql` com `\q`.

---

## 🆘 Se algo deu errado

| O que apareceu | O que é | O que fazer |
|---|---|---|
| `ERROR: relation "dispositivos" does not exist` | Você pulou um passo: a tabela referenciada ainda não foi criada (regra 3) | Volte e rode os blocos na ordem |
| `ERROR: function update_updated_at_column() does not exist` | Você está no banco errado (provavelmente no DW) | Saia com `\q` e entre com `make psql-oltp` |
| O `psql` mostra `liga_sudoers-#` ou `liga_sudoers(#` e nada acontece | Ficou um comando pela metade (faltou `;` ou `)`) | Aperte `Ctrl+C` e cole o bloco inteiro de novo |
| A conferência reclama de tipo ou de `NOT NULL` | Uma coluna foi criada diferente do modelo | Apague só ela (`ALTER TABLE x DROP COLUMN y;`) e cole o bloco de novo |
| Bagunçou tudo e quer recomeçar | — | `make reset-oltp` volta o banco às 6 tabelas do legado |
| Quer ver a resposta pronta | — | `make gabarito-oltp` aplica tudo. O arquivo é [`ddl/gabarito/oltp_evolucao.sql`](../ddl/gabarito/oltp_evolucao.sql) |

Mais em [docs/faq.md](../../docs/faq.md).

---

## ✅ Antes de seguir

* [ ] `make conferir-oltp` mostra **0 pendências**
* [ ] `\dt` lista 13 tabelas
* [ ] Sei explicar por que `peso_gramas` nasceu aceitando nulo e `is_fraude` não
* [ ] Sei por que `carga_pedidos` tem chave primária composta
* [ ] Sei para que serve o trigger de `updated_at`

Você tem um modelo. Falta a prova de que ele funciona com dado de verdade.

---

# ➡️ Continue em [data_simulator/README.md](../../data_simulator/README.md)
