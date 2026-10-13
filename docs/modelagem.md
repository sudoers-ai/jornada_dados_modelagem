# 📐 Do transacional ao dimensional

> ⬅️ [README principal](../README.md)

Este é o texto de referência da disciplina. A trilha mostra **como** fazer;
aqui está o **porquê**. Leia antes da etapa 6, e volte sempre que um conceito
parecer solto.

A ideia que atravessa o documento inteiro:

> O banco transacional e o Data Warehouse guardam **os mesmos fatos do
> mundo**, com **desenhos opostos**, porque respondem a **perguntas opostas**.
> Passar de um para o outro não é copiar: é **transformar**.

---

## 1. Duas perguntas, dois desenhos

Um sistema de vendas faz, o dia inteiro, dois tipos de pergunta ao banco:

| | A pergunta do **site** | A pergunta do **diretor** |
|---|---|---|
| Exemplo | "Grave o pedido 5001 do cliente 42" | "Quanto vendemos por categoria, por mês, neste ano?" |
| Toca em | uma linha | milhões de linhas |
| Acontece | milhares de vezes por minuto | algumas vezes por dia |
| O que não pode | perder ou corromper um pedido | demorar, ou cada um calcular de um jeito |
| Nome | **OLTP** (*Online Transaction Processing*) | **OLAP** (*Online Analytical Processing*) |

Nenhum desenho de tabelas atende bem às duas. Por isso existem dois.

### O desenho transacional: 3ª forma normal

O objetivo é **gravar sem risco**. A técnica é a **normalização**: cada
informação existe em **um lugar só**.

```
categorias ◄── produtos ◄── itens_pedidos ──► pedidos ──► pessoas
```

O nome "Eletronicos" está em uma linha de `categorias`. Os 19 produtos dessa
categoria guardam só o número dela. Se o nome mudar, muda em um lugar, e é
impossível dois produtos discordarem sobre como a categoria se chama.

O preço dessa segurança é pago na **leitura**: para mostrar o nome da
categoria ao lado do valor vendido, é preciso atravessar quatro tabelas.

### O desenho dimensional: star schema

O objetivo é **responder sem pensar**. A técnica é o contrário da
normalização: as informações são **juntadas de propósito**.

```
                 dim_tempo
                     │
   dim_produtos ── fato_pedidos ── dim_pessoas
                     │
               dim_localidade
```

No centro, a **fato**: o que aconteceu, com os números. Em volta, as
**dimensões**: o contexto. Parece uma estrela, e daí o nome.

O texto "Eletronicos" agora está repetido em 19 linhas de `dim_produtos`. Em
troca, qualquer pergunta sobre vendas é a fato e **um salto** até a dimensão
que interessa.

### Por que não usar um só?

* **Só o transacional:** relatórios pesados disputam o banco com as vendas, e
  cada analista reinventa os `JOIN`s (e erra de um jeito diferente).
* **Só o dimensional:** gravar um pedido exigiria atualizar textos repetidos
  em milhares de linhas, e bastaria uma falha para o banco se contradizer.

---

## 2. Fato e dimensão

**Fato** é a tabela do **acontecimento**. Ela responde "quanto?".

* Tem muitas linhas e poucas colunas.
* As colunas são de dois tipos: **chaves** (que apontam para as dimensões) e
  **medidas** (números que se somam: quantidade, valor, peso).
* Cresce para sempre: cada venda nova é uma linha nova.

**Dimensão** é a tabela do **contexto**. Ela responde "quem? o quê? onde?
quando? como?".

* Tem poucas linhas e muitas colunas.
* As colunas são textos e categorias: nome, cidade, categoria, fabricante.
* É por elas que se **filtra** e se **agrupa**.

Um teste simples para decidir onde uma coluna vai:

> Você quer **somar** isto, ou quer **agrupar por** isto?
> Somar → medida, vai para a fato. Agrupar → atributo, vai para a dimensão.

Na Liga Sudoers:

| Coluna | Somar ou agrupar? | Onde fica |
|---|---|---|
| valor do item | somar | `fato_pedidos.valor_total` |
| peso do item | somar | `fato_pedidos.peso_gramas` |
| categoria do produto | agrupar | `dim_produtos.cat_desc` |
| UF da compra | agrupar | `dim_localidade.uf` |
| preço do produto | somar (e muda com o tempo) | `fato_pedidos.valor_unit` |

A última linha costuma surpreender, e está explicada na seção 6.

---

## 3. Grão: a decisão mais importante

**Grão** é a resposta para a pergunta: *"o que é **uma linha** desta fato?"*

A resposta tem que caber numa frase curta, sem "ou" e sem "às vezes":

| Fato | Grão |
|---|---|
| `fato_pedidos` | um item de um pedido |
| `fato_entregas` | um pedido embarcado em um transporte |
| `fato_ciclo_pedido` | um pedido |
| `fato_peso_diario` | um dia de uma transportadora |

Definido o grão, vem a regra que não tem exceção:

> **Toda medida de uma fato precisa estar no grão dela.**

Foi a violação dessa regra que você encontrou na etapa 5. A `fato_pedidos`
antiga tinha grão de **item**, mas a coluna `total` guardava o valor do
**pedido**:

```
 id_pedido | produto            | valor do item | total (do PEDIDO)
-----------+--------------------+---------------+-------------------
         1 | Deserunt Movei 128 |       8935.89 |          10140.44
         1 | Totam Movei 24     |       1204.55 |          10140.44
                                                  ─────────────────
                                    SUM(total) =          20280.88   ← o dobro
```

Nenhuma consulta esperta conserta isso. O erro está no desenho.

**Como escolher o grão:** comece pelo mais fino que o negócio registra. Do
grão fino se chega a qualquer total somando. Do grão grosso não há como
voltar ao detalhe.

**Um processo, uma fato.** Venda e entrega são processos diferentes, com
grãos diferentes. Tentar colocá-los na mesma tabela é o jeito mais comum de
cair no erro acima. Por isso a Liga Sudoers tem `fato_pedidos` **e**
`fato_entregas`.

---

## 4. Chave substituta (`sk_`)

Toda dimensão do DW tem uma chave própria, gerada pelo DW: `sk_pessoa`,
`sk_produto`... É ela que a fato guarda. O `id` do transacional continua na
dimensão, como um atributo qualquer (a *chave de negócio*).

Parece redundante até você precisar de uma destas três coisas:

1. **Guardar histórico.** Com SCD tipo 2 (seção 5), a mesma pessoa tem várias
   linhas na dimensão. O `id` se repete. Só a `sk_` identifica cada linha.
2. **Juntar fontes.** Se a empresa comprar outra, os clientes das duas terão
   `id` 1, 2, 3... A `sk_` é única dentro do DW.
3. **Sobreviver a mudanças na origem.** Se o sistema transacional for trocado
   e os `id` mudarem, as fatos antigas continuam apontando para as mesmas
   `sk_`.

A regra prática:

> **No DW, fato e dimensão se ligam pela `sk_`. Sempre.**

O gráfico "ticket médio por categoria", que você consertou na etapa 8, fazia
`ON fp.sk_produto = dp.id`. Funcionou por anos, porque as duas numerações
coincidiam, e quebrou em silêncio no dia em que deixaram de coincidir.

A única exceção combinada é a `dim_tempo`, cuja chave é a própria data em
formato de número (`20261013`), por conveniência de leitura.

---

## 5. Dimensões que mudam devagar (SCD)

O nome é feio (*Slowly Changing Dimension*); a ideia é simples. Atributos de
dimensão mudam de vez em quando: a pessoa se muda, o produto troca de
categoria. A pergunta é: **o que fazer com o passado?**

### Tipo 1 — Sobrescrever

A linha é atualizada. O valor antigo é esquecido.

```
antes:   sk_produto = 15 | descricao = 'Tenis Corida'
depois:  sk_produto = 15 | descricao = 'Tênis Corrida'
```

Serve quando o passado **não importa**: correção de erro de digitação, ou
atributo que ninguém analisa historicamente. É o que `dim_produtos` e
`dim_transportadora` fazem.

### Tipo 2 — Criar uma versão nova

A linha antiga é **fechada** e nasce uma nova. Três colunas controlam isso:

```
 sk_pessoa | id | nome      | cidade             | dt_inicio  | dt_fim     | is_atual
-----------+----+-----------+--------------------+------------+------------+----------
         7 |  7 | Ravi Rios | Barbosa das Pedras | 1900-01-01 | 2026-08-13 | false
         8 |  7 | Ravi Rios | Souza              | 2026-08-13 |   (nulo)   | true
```

Cada venda aponta para a `sk_pessoa` que valia **no dia da venda**. As compras
antigas do Ravi continuam em Barbosa das Pedras para sempre.

Serve quando o passado **importa**: se a análise é "vendas por cidade", mudar
a cidade do cliente não pode reescrever o relatório do ano passado.

### O que acontece sem a validade

O ETL legado (etapa 5) já criava uma linha nova quando o produto mudava — mas
sem `dt_inicio` e `dt_fim`. Resultado: na hora de carregar a fato, cada venda
casava com **todas** as versões do produto, e as vendas dobravam.

SCD tipo 2 sem data de validade não é histórico. É duplicação.

### Como escolher

| Pergunta | Se sim |
|---|---|
| Alguém vai analisar este atributo **ao longo do tempo**? | tipo 2 |
| É só uma correção, ou ninguém liga para o valor antigo? | tipo 1 |
| Muda toda hora (preço, estoque, saldo)? | **não é dimensão**: é medida, vai para uma fato |

Uma mesma dimensão pode misturar os dois. Em `dim_pessoas`, cidade e UF são
tipo 2; o nome é tipo 1 (se for corrigido, corrige em todas as versões).

---

## 6. Onde mora o preço?

Pergunta clássica de prova, e bom resumo de tudo até aqui.

O preço é um atributo do produto. Então vai para `dim_produtos`?

* Se for **tipo 1**, ao reajustar o preço você perde o preço antigo. A receita
  do ano passado, recalculada, sai errada.
* Se for **tipo 2**, cada reajuste cria uma versão do produto. Com preços
  mudando toda semana, a dimensão explode.

A saída é perceber que o preço que interessa à análise não é "o preço do
produto". É **o preço pelo qual aquela venda aconteceu** — e isso é um número
do acontecimento. É uma **medida**. Mora na fato:

```sql
round(i.valor_total / i.qtde, 2) AS valor_unit   -- o preço NO DIA da venda
```

Se o produto for reajustado amanhã, essa linha não muda. É o histórico de
preços mais barato que existe.

---

## 7. Os três tipos de fato

### Transacional — uma linha por acontecimento

`fato_pedidos`, `fato_entregas`. Aconteceu uma venda, nasce uma linha. É o
tipo mais comum, e o mais flexível: tudo se soma.

### Snapshot periódico — uma linha por período

`fato_peso_diario`: uma linha por **dia** e transportadora. Não registra um
acontecimento; registra **como as coisas estavam** (ou quanto se acumulou)
naquele período.

Serve para o que se consulta sempre do mesmo jeito: em vez de somar 4.641
entregas a cada vez que alguém abre o dashboard, o total do dia fica pronto.

Duas regras de ouro:

* **Não guarde média.** A média de duas médias não é a média do todo. Guarde
  o numerador e o denominador (`peso_total_gramas` e `qtd_pedidos`) e divida
  na consulta.
* Geralmente é **derivado de outra fato**, e é refeito a cada carga.

### Snapshot acumulado — uma linha por processo

`fato_ciclo_pedido`: uma linha por **pedido**, que **vai sendo preenchida**.

```
 id_pedido | dt_criado | dt_pago | dt_separado | dt_enviado | dt_entregue
-----------+-----------+---------+-------------+------------+-------------
      5001 | 13/10     | 13/10   |   (nulo)    |   (nulo)   |   (nulo)     ← hoje
      5001 | 13/10     | 13/10   | 14/10       | 14/10      |   (nulo)     ← amanhã
```

Serve para processos com **começo, meio e fim**, quando a pergunta é sobre o
**tempo entre as etapas**. É a única fato em que `UPDATE` é a rotina.

No transacional, esse mesmo dado é uma tabela de eventos (`status_pedidos`),
com uma linha por mudança. As linhas "deitam" no ETL: cada situação vira uma
coluna de data. É a transformação mais radical da disciplina, e mostra bem
que os dois modelos não são cópia um do outro.

### Como escolher

| A pergunta do negócio é... | Tipo de fato |
|---|---|
| "Quanto aconteceu?" | transacional |
| "Como estava em cada dia / mês?" | snapshot periódico |
| "Quanto tempo leva de uma etapa à outra?" | snapshot acumulado |

---

## 8. Dimensões que não vêm do transacional

Nem tudo que o DW guarda existe na origem.

* **`dim_tempo`** — um calendário. Uma linha por dia, com mês, trimestre, dia
  da semana, fim de semana e feriado. Nenhum sistema transacional tem a
  tabela "dias". É a dimensão mais usada de qualquer DW.
* **`dim_localidade`** — as 27 UFs, com região e a regra "é área atendida?".
  A regra existia: estava num `CASE` dentro de um gráfico.

E há os **atributos derivados**, que nascem no ETL:

| Atributo | Como nasce |
|---|---|
| `dim_dispositivo.fabricante` | extraído do texto do modelo |
| `dim_dispositivo.qtd_contas` | contagem de pessoas diferentes por aparelho |
| `dim_dispositivo.is_compartilhado` | regra: 3 contas ou mais |
| `fato_pedidos.peso_gramas` | quantidade × peso do produto |
| `fato_entregas.dias_atraso` | entrega − previsão |
| `fato_entregas.valor_frete` | frete do caminhão, rateado pelo peso |

Esta é a diferença entre um DW e um *backup*: o DW **acrescenta
conhecimento**. Uma regra que estava espalhada em dez relatórios passa a
existir em um lugar, calculada uma vez.

---

## 9. O mapa completo

| No transacional | No dimensional | Transformação | Conceito |
|---|---|---|---|
| `pedidos.dt_venda` | `dim_tempo` | uma coluna vira uma tabela | dimensão sem origem |
| `auditoria_pedidos.uf` | `dim_localidade` | a regra de negócio vira coluna | dimensão sem origem |
| `pessoas` + `enderecos` | `dim_pessoas` | junta; cada endereço vira uma versão | SCD tipo 2 |
| `produtos` + `categorias` | `dim_produtos` | junta; sobrescreve | desnormalização, SCD tipo 1 |
| `dispositivos` | `dim_dispositivo` | acrescenta atributos calculados | atributo derivado |
| `transportadoras` | `dim_transportadora` | ganha chave substituta | chave substituta |
| `pagamentos.forma` | `dim_forma_pagamento` | um atributo vira entidade | — |
| `pedidos` + `itens` + `auditoria` + `pagamentos` | `fato_pedidos` | quatro tabelas viram uma; `id` vira `sk_` | fato transacional, grão |
| `transportes` + `carga_pedidos` | `fato_entregas` | frete rateado; medidas calculadas | rateio, dimensão com dois papéis |
| `status_pedidos` | `fato_ciclo_pedido` | linhas viram colunas | snapshot acumulado |
| (não existe) | `fato_peso_diario` | agregado de outra fato | snapshot periódico |

---

## 10. O ETL em uma página

| Passo | O que faz | Por quê |
|---|---|---|
| **Extract** | Copia as tabelas da origem para a *staging*, sem mexer | Tirar uma foto consistente e não atrapalhar a operação |
| **Transform** | Junta, calcula, troca `id` por `sk_`, dá forma | É aqui que o modelo dimensional nasce |
| **Load** | Grava nas dimensões e depois nas fatos | Dimensões primeiro: a fato precisa das `sk_` |

Três qualidades de um bom ETL, que você viu na etapa 7:

* **Idempotente** — rodar duas vezes dá o mesmo resultado de rodar uma. É o
  que permite reprocessar depois de uma falha. (`MERGE`, e não `INSERT` cego.)
* **Incremental** — só mexe no que mudou. (`WHEN MATCHED AND ... IS DISTINCT
  FROM ...`)
* **Verificável** — tem prova. (Cada passo termina comparando o destino com a
  origem; o `make validar` confere tudo.)

E uma consequência prática: o DW é sempre **um pouco atrasado** em relação ao
transacional — tão atrasado quanto o intervalo entre duas cargas. De quanto
em quanto tempo o ETL roda é uma decisão de negócio.

---

## 11. Erros clássicos (todos presentes no legado desta disciplina)

| Erro | Sintoma | Onde você viu |
|---|---|---|
| Medida no grão errado | Somas infladas | `total` do pedido na fato de itens (etapa 5) |
| Nome que engana | Consultas "que só fulano entende" | `valor_unit` que era o total do item (etapa 5) |
| Histórico sem validade | Linhas duplicadas na fato | `dim_produtos` com duas versões (etapa 5) |
| Juntar `sk_` com `id` | Resultado errado, sem erro | Gráfico de ticket médio (etapa 8) |
| Regra de negócio no relatório | A regra envelhece e ninguém vê | `CASE` do geohash (etapas 5 e 8) |
| Média guardada | Totais que não fecham | Evitado em `fato_peso_diario` (etapa 6) |
| Média no grão errado | Indicador com nome de uma coisa e conta de outra | "Ticket médio" por produto (etapa 8) |

---

## Para ir além

* Ralph Kimball e Margy Ross, *The Data Warehouse Toolkit* — a referência de
  modelagem dimensional. Os termos deste documento (grão, fato transacional,
  snapshot periódico e acumulado, SCD tipo 1 e 2, dimensão com vários papéis)
  vêm de lá.
* [Glossário](./glossario.md) — os mesmos termos, em duas linhas cada.
* [Desafios](../desafios/desafios.md) — para praticar o que não coube na
  trilha: SCD tipo 2 em produto, dimensão *junk*, fato sem medida, carga
  incremental.
