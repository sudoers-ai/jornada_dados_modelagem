# 7️⃣ O ETL novo — transformando o dado

> ⬅️ Anterior: [6. Evoluir o dimensional](../modelagem/05_evolucao_dw/README.md) · [README principal](../README.md) · Etapa 7 de 9

Você tem dois modelos: o transacional cheio, o dimensional vazio. O que liga
um ao outro é o **ETL**.

Nesta etapa você roda o ETL **um passo de cada vez**, e a cada passo vê o dado
mudar de forma. O objetivo não é decorar SQL: é enxergar, tabela por tabela,
o que acontece com o dado no caminho do transacional até o dimensional.

```
   TRANSACIONAL                      DATA WAREHOUSE
  ┌────────────┐   E      ┌──────────────────────────────────────────┐
  │ 13 tabelas │ ───────► │ stg.*  ──T──►  7 dimensões  ──►  4 fatos │
  │   (3FN)    │ Extract  │ (cópia)  Transform            Load       │
  └────────────┘          └──────────────────────────────────────────┘
```

| Letra | O que é | Onde acontece aqui |
|---|---|---|
| **E** — *Extract* | Tirar o dado da origem | Passos 00 e 01 |
| **T** — *Transform* | Mudar a forma do dado | Dentro de cada passo, de 02 a 12 |
| **L** — *Load* | Gravar no destino | O `INSERT` ou `MERGE` no fim de cada passo |

> 📺 **Para assistir antes** (opcional, ~17 min). Os vídeos mostram o ambiente **antigo** do `liga_sudoers` (6 tabelas, ETL no Apache Hop): é o ponto de partida desta disciplina, não o passo a passo desta etapa.
>
> - [Data Modeling 07 - O poder do ETL e do SQL para manipular os dados](https://www.youtube.com/watch?v=DHinno_tFmc&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=8)
> - [Data Modeling 08 - Movendo dados com ETL](https://www.youtube.com/watch?v=QoO1Q0JsrBs&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=9)

---

## Como trabalhar nesta etapa

Os 13 passos estão em [`etl/sql/`](./sql/), um arquivo por tabela, numerados
na ordem em que precisam rodar:

```
etl/sql/
├── 00_conexao_oltp.sql         a ponte entre os dois bancos
├── 01_staging.sql              a fotografia do transacional
├── 02_dim_tempo.sql            ┐
├── 03_dim_localidade.sql       │
├── 04_dim_produtos.sql         │
├── 05_dim_transportadora.sql   ├─ dimensões (sempre antes das fatos)
├── 06_dim_forma_pagamento.sql  │
├── 07_dim_dispositivo.sql      │
├── 08_dim_pessoas.sql          ┘
├── 09_fato_pedidos.sql         ┐
├── 10_fato_entregas.sql        ├─ fatos
├── 11_fato_ciclo_pedido.sql    │
└── 12_fato_peso_diario.sql     ┘
```

Para cada passo, o ritual é o mesmo:

1. **Abra o arquivo e leia o cabeçalho.** Cada um começa explicando, em
   português, o que aquela transformação faz e por quê.
2. **Rode o passo:** `make etl-passo p=NN`
3. **Leia a prova** que aparece no fim da saída.

> **Por que as dimensões vêm antes das fatos?** Porque a fato guarda as `sk_`
> das dimensões. Para trocar o `id` de um produto pela `sk_produto`, a
> dimensão precisa já ter aquele produto.

---

## O portão

Antes de carregar, confirme que o desenho está certo:

<!-- rodar: shell -->
```bash
make conferir-dw
```

```
✅ Modelagem do DIMENSIONAL (DW) conferida: 11 tabelas, 110 colunas, 15 FKs, 0 pendências.
```

Se aparecerem pendências, volte à [etapa 6](../modelagem/05_evolucao_dw/README.md).
O `make etl` faz essa mesma conferência sozinho e se recusa a rodar com o
modelo errado.

> Os números de pessoas e pedidos que você verá daqui em diante dependem de
> quantos o streaming gerou na etapa 4: os seus serão um pouco diferentes dos
> deste roteiro. **O que precisa bater são as provas**, que comparam uma
> coluna com a outra.

---

# Extract

## Passo 00 — A ponte entre os dois bancos

O DW e o transacional são dois servidores separados. O `postgres_fdw` faz as
tabelas do transacional aparecerem dentro do DW, no schema `oltp`, como se
fossem locais.

<!-- rodar: shell -->
```bash
make etl-passo p=00
```

```
▶ etl/sql/00_conexao_oltp.sql
SET
CREATE EXTENSION
DROP SERVER
CREATE SERVER
CREATE USER MAPPING
DROP SCHEMA
CREATE SCHEMA
IMPORT FOREIGN SCHEMA

--- prova: o DW esta lendo o transacional AO VIVO (nada foi copiado ainda)
 pessoas_no_oltp | pedidos_no_oltp |     venda_mais_recente
-----------------+-----------------+----------------------------
             501 |            5002 | 2026-10-13 18:27:43.877581
(1 row)
```

**Nenhum dado foi copiado.** `oltp.pedidos` é uma janela: cada consulta a ela
vai até o outro servidor buscar a resposta.

## Passo 01 — Staging: a fotografia

<!-- rodar: shell -->
```bash
make etl-passo p=01
```

```
▶ etl/sql/01_staging.sql
SET
BEGIN
DROP SCHEMA
CREATE SCHEMA
SELECT 501
SELECT 581
SELECT 12
SELECT 200
...
COMMIT
...
--- prova: a fotografia (linhas copiadas por tabela)
      tabela       | linhas
-------------------+--------
 pessoas           |    501
 enderecos         |    581
 produtos          |    200
 dispositivos      |    584
 pedidos           |   5002
 itens_pedidos     |  14981
 auditoria_pedidos |   5002
 pagamentos        |   5002
 status_pedidos    |  24118
 transportes       |    592
 carga_pedidos     |   4640
(11 rows)
```

Agora sim o dado foi copiado: cada `SELECT 5002` é uma tabela do transacional
que virou uma tabela do schema `stg`, **sem nenhuma transformação**.

**Por que copiar antes de transformar?**

* **Para tirar uma foto.** O transacional está vivo: entra pedido a cada
  segundo. Se cada dimensão e cada fato lesse de lá num instante diferente,
  as contas não fechariam (um pedido apareceria na fato, mas o cliente dele
  ainda não estaria na dimensão). A staging congela um instante, e todo o
  resto do ETL trabalha sobre ele. É por isso que as cópias estão entre
  `BEGIN` e `COMMIT`.
* **Para não atrapalhar quem vende.** As transformações são pesadas. Rodando
  sobre a cópia, elas não disputam o banco com o site.

Daqui em diante, o ETL **não toca mais no transacional**.

---

# Transform + Load: as dimensões

## Passo 02 — `dim_tempo`: uma coluna vira uma tabela

<!-- rodar: shell -->
```bash
make etl-passo p=02
```

```
▶ etl/sql/02_dim_tempo.sql
INSERT 0 730

--- prova: o calendario
 dias | primeiro_dia | ultimo_dia | fins_de_semana | feriados
------+--------------+------------+----------------+----------
  730 | 2026-01-01   | 2027-12-31 |            208 |       18
(1 row)

 sk_tempo |    data    |  nome_dia   | nome_mes | trimestre | is_fim_semana | is_feriado
----------+------------+-------------+----------+-----------+---------------+------------
 20261013 | 2026-10-13 | Terça-feira | Outubro  |         4 | f             | f
(1 row)
```

A segunda tabela da prova é **o dia de hoje** como o DW o enxerga. No
transacional, hoje é só um valor dentro de `dt_venda`. Aqui é uma linha, com
nome do dia, mês, trimestre e se é feriado.

Repare que esta dimensão **não leu quase nada da origem**: usou só a data da
venda mais antiga para saber onde o calendário começa. O resto foi gerado
(`generate_series`). E ela vai até o fim do ano que vem, porque entregas
previstas caem no futuro.

> 💡 **O que você aprendeu:** nem toda dimensão vem do transacional. Algumas
> guardam conhecimento do negócio que não está em sistema nenhum.

## Passo 03 — `dim_localidade`: a regra vira dado

<!-- rodar: shell -->
```bash
make etl-passo p=03
```

```
▶ etl/sql/03_dim_localidade.sql
INSERT 0 27

--- prova: 27 UFs, 3 atendidas
    regiao    | ufs | atendidas
--------------+-----+-----------
 Centro-Oeste |   4 |         0
 Nordeste     |   9 |         0
 Norte        |   7 |         0
 Sudeste      |   4 |         3
 Sul          |   3 |         0
(5 rows)
```

A regra "a Liga Sudoers só atende SP, MG e RJ" saiu do `CASE` do dashboard e
agora é a coluna `is_area_atendida`. Para mudar a regra, muda-se um dado.

> 💡 **O que você aprendeu:** regra de negócio mora no modelo, não no gráfico.

## Passo 04 — `dim_produtos`: desnormalizar (SCD tipo 1)

<!-- rodar: shell -->
```bash
make etl-passo p=04
```

```
▶ etl/sql/04_dim_produtos.sql
MERGE 200

--- prova: a categoria agora esta DENTRO do produto, sem JOIN
  categoria  | produtos | peso_medio_gramas
-------------+----------+-------------------
 Alimentos   |       14 |              2304
 Automotivo  |       22 |              9998
 Beleza      |       21 |               352
 ...
 Moveis      |       22 |             21702
 Pet         |       18 |              6950
 Vestuario   |       19 |               597
(12 rows)
```

No transacional, a consulta da prova precisaria de `produtos JOIN categorias`.
Aqui ela lê **uma tabela**. O texto "Moveis" está repetido em 22 linhas — e
está tudo bem. No DW, repetir é o preço de não precisar juntar.

Abra o arquivo e veja o comando `MERGE`. Ele é o coração de um ETL
incremental e diz, numa frase:

> "Compare a origem com o destino pelo `id`. Quem **mudou**, atualize. Quem
> **não existe**, insira. Quem está igual, não toque."

`MERGE 200` significa que 200 linhas foram inseridas ou alteradas. Guarde
esse número: mais adiante você vai rodar de novo e ver `MERGE 0`.

> 💡 **O que você aprendeu:** *desnormalizar* é juntar no DW o que o
> transacional separa. *SCD tipo 1* é sobrescrever quando muda.

## Passo 05 — `dim_transportadora`: a chave substituta

<!-- rodar: shell -->
```bash
make etl-passo p=05
```

```
▶ etl/sql/05_dim_transportadora.sql
MERGE 5

--- prova: sk_ (chave do DW) ao lado do id (chave do transacional)
 sk_transportadora | id |        nome        | custo_por_kg
-------------------+----+--------------------+--------------
                 1 |  1 | Rápido Bandeirante |         4.90
                 2 |  2 | TransMinas Cargas  |         5.60
                 3 |  3 | Expresso Carioca   |         6.20
                 4 |  4 | Sudeste Log        |         7.80
                 5 |  5 | Barato Fretes      |         3.20
(5 rows)
```

Aqui `sk_transportadora` e `id` coincidem, **por acaso**: as cinco entraram
na mesma ordem. Não conte com isso. No passo 08 você verá as duas se
separarem, e na etapa 8 vai encontrar um gráfico antigo que estava errado
justamente por tratar `sk_` e `id` como a mesma coisa.

> 💡 **O que você aprendeu:** a `sk_` é a chave do DW; o `id` vira só mais um
> atributo. Quem liga fato e dimensão é sempre a `sk_`.

## Passo 06 — `dim_forma_pagamento`: um atributo vira entidade

<!-- rodar: shell -->
```bash
make etl-passo p=06
```

```
▶ etl/sql/06_dim_forma_pagamento.sql
INSERT 0 4

--- prova: 4 formas de pagamento, com descricao e atributo derivado
 sk_forma_pagamento |     forma      |     descricao     | is_a_vista
--------------------+----------------+-------------------+------------
                  1 | boleto         | Boleto bancário   | t
                  2 | pix            | Pix               | t
                  3 | cartao_credito | Cartão de crédito | f
                  4 | cartao_debito  | Cartão de débito  | t
(4 rows)
```

Não existe tabela "formas de pagamento" no transacional. O ETL as
**descobriu** com um `SELECT DISTINCT` na coluna `pagamentos.forma`, e
enriqueceu: `descricao` é um nome que cabe num gráfico, `is_a_vista` é um
atributo novo.

> 💡 **O que você aprendeu:** tudo pelo que se agrupa ou filtra pode virar
> dimensão, mesmo que na origem seja só um texto.

## Passo 07 — `dim_dispositivo`: atributos que nascem no ETL

<!-- rodar: shell -->
```bash
make etl-passo p=07
```

```
▶ etl/sql/07_dim_dispositivo.sql
MERGE 584

--- prova: os aneis de fraude aparecem com um filtro
 device_id  |      modelo      | fabricante | qtd_contas
------------+------------------+------------+------------
 d-2ad820ca | iPhone 13        | Apple      |          5
 d-32df8d45 | Motorola Edge 40 | Motorola   |          5
 d-3c6841d6 | iPhone 15        | Apple      |          5
 d-855b6c5b | iPad Air         | Apple      |          5
 d-c891d55d | Pixel 8          | Google     |          5
 d-ca0553a2 | Web Chrome       | Navegador  |          4
(6 rows)
```

**São os mesmos seis anéis de fraude da etapa 4.** Lá você precisou de três
tabelas, `GROUP BY` e `HAVING`. A consulta da prova é esta:

```sql
SELECT device_id, modelo, fabricante, qtd_contas
FROM dim_dispositivo
WHERE is_compartilhado;
```

Um `WHERE`. A conta difícil foi feita **uma vez**, dentro do ETL, e o
resultado ficou guardado como um atributo da dimensão. Abra o arquivo e
encontre a subconsulta que calcula `qtd_contas`: é a sua consulta da etapa 4.

> 💡 **O que você aprendeu:** transformar é também **calcular**. O DW guarda
> respostas prontas para perguntas que seriam caras de fazer toda hora.

## Passo 08 — `dim_pessoas`: guardar o passado (SCD tipo 2)

<!-- rodar: shell -->
```bash
make etl-passo p=08
```

```
▶ etl/sql/08_dim_pessoas.sql
INSERT 0 581
UPDATE 501
UPDATE 0

--- prova 1: mais linhas na dimensao do que pessoas (quem se mudou tem 2 ou mais)
 linhas_na_dimensao | pessoas | versoes_atuais | versoes_antigas
--------------------+---------+----------------+-----------------
                581 |     501 |            501 |              80
(1 row)

--- prova 2: a historia de uma pessoa que se mudou
 sk_pessoa | id |   nome    |       cidade       | uf | dt_inicio  |   dt_fim   | is_atual
-----------+----+-----------+--------------------+----+------------+------------+----------
         7 |  7 | Ravi Rios | Barbosa das Pedras | MG | 1900-01-01 | 2026-08-13 | f
         8 |  7 | Ravi Rios | Souza              | MG | 2026-08-13 |            | t
(2 rows)
```

Aí está o Ravi Rios. **Um `id`, duas linhas, duas `sk_pessoa`.**

| | Linha 1 | Linha 2 |
|---|---|---|
| `sk_pessoa` | 7 | 8 |
| `id` (o do transacional) | 7 | 7 |
| Cidade | Barbosa das Pedras | Souza |
| Vale de... | sempre (`1900-01-01`) | 13/08/2026 |
| ...até | 13/08/2026 | hoje (`dt_fim` nulo) |

As compras que o Ravi fez antes de 13/08 vão apontar para a `sk_pessoa = 7` e
contar para Barbosa das Pedras, **para sempre**. As de depois apontam para a
8. O relatório de vendas por cidade do semestre passado não muda só porque
ele se mudou.

Compare com o **problema 2** da etapa 5: lá o produto também ganhou duas
linhas, e as vendas dobraram. A diferença está em `dt_inicio` e `dt_fim`.
Com elas, cada venda casa com **exatamente uma** versão.

E é aqui que `sk_` e `id` se separam de vez: são 501 pessoas e 581 linhas. O
`id` deixou de identificar uma linha. Só a `sk_pessoa` identifica.

O arquivo tem três comandos — leia os comentários de cada um:

| Na saída | O que fez |
|---|---|
| `INSERT 0 581` | cada endereço que cada pessoa já teve virou uma versão |
| `UPDATE 501` | fechou as versões antigas (`dt_fim`) e marcou a atual |
| `UPDATE 0` | corrigiria nomes alterados em todas as versões (não havia nenhum) |

> 💡 **O que você aprendeu:** *SCD tipo 2* preserva o passado criando uma
> versão nova a cada mudança, com data de validade. É por causa dele que o DW
> precisa de chave substituta.

---

# Transform + Load: as fatos

## Passo 09 — `fato_pedidos`: a fato transacional

**Grão: uma linha por item de pedido.**

<!-- rodar: shell -->
```bash
make etl-passo p=09
```

```
▶ etl/sql/09_fato_pedidos.sql
MERGE 14981

--- prova 1: a soma da fato BATE com o transacional (nada contado em dobro)
 soma_na_fato | soma_dos_pedidos_no_oltp | linhas_na_fato | itens_no_oltp
--------------+--------------------------+----------------+---------------
  95229115.97 |              95229115.97 |          14981 |         14981
(1 row)

--- prova 2: taxa de fraude por UF, em 1 JOIN (no transacional seriam 3)
 uf | is_area_atendida | pedidos | fraudes | pct_fraude
----+------------------+---------+---------+------------
 RJ | t                |    1755 |      69 |        3.9
 MG | t                |    1645 |      60 |        3.6
 SP | t                |    1556 |      60 |        3.9
 BA | f                |      11 |      11 |      100.0
 RS | f                |       9 |       9 |      100.0
 PE | f                |       7 |       7 |      100.0
 DF | f                |       6 |       6 |      100.0
 CE | f                |       6 |       6 |      100.0
 PR | f                |       4 |       4 |      100.0
 AM | f                |       3 |       3 |      100.0
(10 rows)
```

**Prova 1 — o erro da etapa 5 acabou.** As duas primeiras colunas são
idênticas: a soma da fato é o faturamento de verdade. Lá o DW mostrava 3,67
vezes mais. A diferença é que a medida agora é o valor do **item**, no mesmo
grão da tabela.

**Prova 2 — a Demanda 1 começa a ser respondida.** Toda compra feita de fora
de SP, MG e RJ é fraude (100%). Essa consulta junta a fato com **uma**
dimensão.

Abra o arquivo: é o comando mais importante do ETL. Repare em quatro coisas.

**1. Quatro tabelas viram uma.** `pedidos`, `itens_pedidos`,
`auditoria_pedidos` e `pagamentos` entram; uma linha por item sai.

**2. Os `id` são trocados por `sk_`.** Cada `JOIN dim_...` existe para isso:

```sql
JOIN dim_produtos    dpr ON dpr.id = i.id_produto        -- entra o id, sai a sk_produto
JOIN dim_dispositivo ddi ON ddi.device_id = a.device_id  -- entra o device_id, sai a sk_dispositivo
```

**3. A pessoa é procurada pela data.** Este é o `JOIN` que faz o SCD tipo 2
funcionar:

```sql
JOIN dim_pessoas dpe ON dpe.id = p.id_pessoa
                    AND p.dt_venda >= dpe.dt_inicio
                    AND p.dt_venda <  COALESCE(dpe.dt_fim, 'infinity')
```

"A versão desta pessoa que valia **no dia da venda**."

**4. Nascem medidas que não existiam.**

```sql
round(i.valor_total / i.qtde, 2)  AS valor_unit   -- o preço NO DIA da venda
i.qtde * pr.peso_gramas           AS peso_gramas  -- o peso do item
```

`valor_unit` agora é unitário de verdade. E ele é o preço **daquela venda**:
se o produto for reajustado amanhã, esta linha não muda.

> 💡 **O que você aprendeu:** a fato é onde tudo se encontra. Ela guarda
> chaves (para as dimensões) e medidas (no grão certo), e nada mais.

## Passo 10 — `fato_entregas`: outro processo, outro grão

**Grão: uma linha por pedido embarcado em um transporte.**

<!-- rodar: shell -->
```bash
make etl-passo p=10
```

```
▶ etl/sql/10_fato_entregas.sql
MERGE 4640

--- prova 1: o rateio fecha (a diferenca de centavos e o arredondamento de cada linha)
 frete_na_fato | frete_no_oltp | diferenca | linhas_na_fato | cargas_no_oltp
---------------+---------------+-----------+----------------+----------------
    1085466.78 |    1085465.55 |      1.23 |           4640 |           4640
(1 row)

--- prova 2: a pergunta da Demanda 2 - custo e pontualidade por transportadora
        nome        | custo_por_kg | entregas | pct_atrasadas | media_dias_transito
--------------------+--------------+----------+---------------+---------------------
 Barato Fretes      |         3.20 |     1302 |          42.2 |                 3.8
 Rápido Bandeirante |         4.90 |      866 |           5.8 |                 2.4
 TransMinas Cargas  |         5.60 |      780 |          11.0 |                 3.7
 Expresso Carioca   |         6.20 |      848 |           7.1 |                 3.0
 Sudeste Log        |         7.80 |      844 |           4.4 |                 2.7
(5 rows)
```

**Prova 2 é a resposta da Demanda 2**, e ela traz uma descoberta: a **Barato
Fretes** é a mais barata por quilo (R$ 3,20) e atrasa **42%** das entregas. A
Sudeste Log custa mais que o dobro e atrasa 4%. Era essa a informação que a
logística precisava para negociar — e ela não existia em nenhum relatório.

**Prova 1 — o rateio.** No transacional o frete é do caminhão. A fato está no
grão do pedido, então o ETL distribuiu o valor pelo peso de cada pedido:

```sql
round(t.valor_frete * w.peso_gramas / t.peso_total_gramas, 2)  AS valor_frete
```

Somando os pedidos, o total volta (a diferença de R$ 1,23 em mais de um
milhão é o arredondamento de 4.640 linhas para duas casas).

> 💡 **O que você aprendeu:** quando um valor está num grão mais alto que o
> da fato, ele é **rateado**. E medidas como `dias_atraso` nascem no ETL, com
> uma regra só, para todos os relatórios.

## Passo 11 — `fato_ciclo_pedido`: as linhas deitam (snapshot acumulado)

**Grão: uma linha por pedido, atualizada a cada marco.**

<!-- rodar: shell -->
```bash
make etl-passo p=11
```

```
▶ etl/sql/11_fato_ciclo_pedido.sql
MERGE 5002

--- prova 1: o funil - quantos pedidos ja passaram por cada marco
 criados | pagos | separados | enviados | entregues | cancelados | devolvidos
---------+-------+-----------+----------+-----------+------------+------------
    5002 |  4759 |      4701 |     4640 |      4554 |        332 |        130
(1 row)

--- prova 2: a pergunta da Demanda 3 - quanto tempo leva cada etapa (em horas)
 media_ate_pagamento | media_ate_envio | media_ate_entrega
---------------------+-----------------+-------------------
                 4.8 |            44.5 |             116.6
(1 row)
```

24.118 linhas de `status_pedidos` viraram 5.002 linhas, uma por pedido.

**Prova 1 é o funil da Demanda 3**: de 5.002 pedidos criados, 4.554 foram
entregues. A consulta é só `count(dt_pago)`, `count(dt_enviado)`... porque
cada marco é uma coluna, e `count` ignora as nulas.

**Prova 2 mostra onde o processo demora**: do pedido ao pagamento, 5 horas;
até o envio, 44; até a entrega, 117 (quase 5 dias).

Abra o arquivo e procure o *pivot*, que é a transformação em si:

```sql
max(dt_evento) FILTER (WHERE status = 'pago')     AS dt_pago,
max(dt_evento) FILTER (WHERE status = 'enviado')  AS dt_enviado,
```

Cada linha de evento vira uma coluna de data.

> 💡 **O que você aprendeu:** o *snapshot acumulado* acompanha um processo
> que tem começo, meio e fim. A linha nasce incompleta e é preenchida com o
> tempo.

## Passo 12 — `fato_peso_diario`: o agregado (snapshot periódico)

**Grão: uma linha por dia e transportadora.**

<!-- rodar: shell -->
```bash
make etl-passo p=12
```

```
▶ etl/sql/12_fato_peso_diario.sql
BEGIN
TRUNCATE TABLE
INSERT 0 482
COMMIT

--- prova 1: o agregado fecha com a fato de origem
 peso_no_agregado | peso_na_fato_entregas | linhas_no_agregado | linhas_na_fato_entregas
------------------+-----------------------+--------------------+-------------------------
        204865500 |             204865500 |                482 |                    4640
(1 row)

--- prova 2: a pergunta da Demanda 2 - peso medio por pedido, por mes
 ano  | mes | nome_mes | pedidos | peso_total_kg | peso_medio_kg_por_pedido | custo_real_por_kg
------+-----+----------+---------+---------------+--------------------------+-------------------
 2026 |   4 | Abril    |     340 |         15097 |                    44.40 |              5.03
 2026 |   5 | Maio     |     777 |         34877 |                    44.89 |              5.36
 2026 |   6 | Junho    |     798 |         34621 |                    43.38 |              5.34
 2026 |   7 | Julho    |     821 |         35934 |                    43.77 |              5.18
 2026 |   8 | Agosto   |     794 |         33988 |                    42.81 |              5.23
 2026 |   9 | Setembro |     784 |         35677 |                    45.51 |              5.50
 2026 |  10 | Outubro  |     326 |         14670 |                    45.00 |              5.30
(7 rows)
```

4.640 entregas viraram 482 linhas, e o peso total é **idêntico** (prova 1).
Menos linhas, mesma verdade.

A prova 2 é o que a diretoria pediu: o peso médio por pedido, mês a mês. E
veja como ele é calculado — não existe coluna de média na tabela:

```sql
sum(peso_total_gramas) / sum(qtd_pedidos)
```

Duas coisas tornam esta fato diferente das outras:

* **Ela nasce de outra fato** (`fato_entregas`), não do transacional.
* **Ela é refeita inteira a cada carga** (`TRUNCATE` + `INSERT`), dentro de
  uma transação. É pequena e derivada: recalcular é mais simples e mais
  seguro do que atualizar.

> 💡 **O que você aprendeu:** o *snapshot periódico* é uma resposta
> pré-calculada por período. E média não se guarda: guardam-se os
> ingredientes dela.

---

# O ETL inteiro

## Rode tudo de novo: nada muda

Um bom ETL pode ser rodado duas vezes sem estragar nada. Isso se chama
**idempotência**, e é o que permite reprocessar depois de uma falha.

<!-- rodar: shell -->
```bash
make etl | grep -E "▶|MERGE|INSERT|UPDATE|✅"
```

```
✅ Modelagem do DIMENSIONAL (DW) conferida: 11 tabelas, 110 colunas, 15 FKs, 0 pendências.
▶ etl/sql/00_conexao_oltp.sql
▶ etl/sql/01_staging.sql
▶ etl/sql/02_dim_tempo.sql
INSERT 0 0
▶ etl/sql/03_dim_localidade.sql
INSERT 0 0
▶ etl/sql/04_dim_produtos.sql
MERGE 0
▶ etl/sql/05_dim_transportadora.sql
MERGE 0
▶ etl/sql/06_dim_forma_pagamento.sql
INSERT 0 0
▶ etl/sql/07_dim_dispositivo.sql
MERGE 0
▶ etl/sql/08_dim_pessoas.sql
INSERT 0 0
UPDATE 0
UPDATE 0
▶ etl/sql/09_fato_pedidos.sql
MERGE 0
▶ etl/sql/10_fato_entregas.sql
MERGE 0
▶ etl/sql/11_fato_ciclo_pedido.sql
MERGE 0
▶ etl/sql/12_fato_peso_diario.sql
INSERT 0 482
✅ ETL concluido.
```

**Tudo zero.** Nenhum pedido novo entrou no transacional, então o ETL não
teve o que fazer (só a `fato_peso_diario` mostra 482, porque ela é sempre
refeita). Compare com o ETL antigo da etapa 5, que a cada rodada com um
produto alterado **duplicava vendas**.

## Agora com a operação viva

Ligue o streaming em segundo plano e deixe-o trabalhar por um minuto:

<!-- rodar: shell -->
```bash
make streaming-fundo
sleep 60
```

(Em outro terminal, `make streaming-logs` mostra o que ele está fazendo.
`Ctrl+C` sai dos logs sem desligar o streaming.)

Rode o ETL outra vez:

<!-- rodar: shell -->
```bash
make etl | grep -E "▶|MERGE|INSERT|UPDATE|✅"
```

```
...
▶ etl/sql/07_dim_dispositivo.sql
MERGE 1
▶ etl/sql/08_dim_pessoas.sql
INSERT 0 5
UPDATE 5
UPDATE 0
▶ etl/sql/09_fato_pedidos.sql
MERGE 60
▶ etl/sql/10_fato_entregas.sql
MERGE 10
▶ etl/sql/11_fato_ciclo_pedido.sql
MERGE 23
...
```

(Os seus números serão outros.) Agora o ETL teve trabalho, e **só mexeu no
que mudou**: algumas dezenas de linhas, e não as 15 mil. Cada número conta
uma história:

| Na saída | O que aconteceu no transacional |
|---|---|
| `dim_pessoas: INSERT 5` | chegaram clientes novos e pessoas se mudaram: cada um é uma versão nova |
| `dim_pessoas: UPDATE 5` | as versões antigas de quem se mudou foram **fechadas** |
| `fato_pedidos: MERGE 60` | itens de pedidos novos, mais pedidos antigos que mudaram de situação |
| `fato_entregas: MERGE 10` | caminhões que chegaram: `dt_entrega` deixou de ser nula |
| `fato_ciclo_pedido: MERGE 23` | pedidos que avançaram: mais uma coluna de data preenchida |

### Veja o SCD tipo 2 acontecer

No `psql` do DW (`make psql-dw`), procure quem se mudou **hoje**:

<!-- rodar: dw -->
```sql
SELECT sk_pessoa, id, nome, cidade, uf,
       dt_inicio::timestamp(0), dt_fim::timestamp(0), is_atual
FROM dim_pessoas
WHERE id IN (SELECT id FROM dim_pessoas WHERE dt_inicio >= current_date)
  AND id <= 500
ORDER BY id, dt_inicio
LIMIT 6;
```

```
 sk_pessoa | id  |         nome          | cidade  | uf |      dt_inicio      |       dt_fim        | is_atual
-----------+-----+-----------------------+---------+----+---------------------+---------------------+----------
        46 |  40 | Enzo Sales            | da Cruz | RJ | 1900-01-01 00:00:00 | 2026-10-13 18:28:49 | f
       582 |  40 | Enzo Sales            | Silva   | RJ | 2026-10-13 18:28:49 |                     | t
       580 | 207 | Srta. Ana Julia Gomes | Castro  | SP | 1900-01-01 00:00:00 | 2026-10-13 18:27:54 | f
       581 | 207 | Srta. Ana Julia Gomes | Farias  | SP | 2026-10-13 18:27:54 |                     | t
       286 | 251 | Sra. Bianca Sá        | Novaes  | MG | 1900-01-01 00:00:00 | 2026-10-13 18:28:14 | f
       583 | 251 | Sra. Bianca Sá        | Costa   | RJ | 2026-10-13 18:28:14 |                     | t
(6 rows)
```

(As pessoas serão outras no seu banco: o streaming sorteia quem se muda.)

São as mudanças de endereço que o streaming fez há poucos minutos. Cada uma
virou duas linhas: a versão antiga, agora com `dt_fim` e `is_atual = false`,
e a nova. Todas as compras antigas dessas pessoas continuam presas à cidade
antiga.

### Veja o snapshot acumulado ser preenchido

<!-- rodar: dw -->
```sql
SELECT id_pedido, status_atual, dt_criado::time(0) AS criado,
       dt_pago::time(0) AS pago, dt_cancelado::time(0) AS cancelado,
       horas_ate_pagamento, is_fraude
FROM fato_ciclo_pedido
WHERE id_pedido > 5000
ORDER BY id_pedido
LIMIT 6;
```

São os pedidos que nasceram no streaming. Alguns já têm `dt_pago`; outros
ainda estão em `criado`, com a data de pagamento nula. Rode o ETL daqui a um
minuto e consulte de novo: linhas que estavam incompletas terão avançado.

Saia do `psql` com `\q`.

> **Pode deixar o streaming ligado** para a próxima etapa: os dashboards
> ficam mais interessantes com dado chegando. Para desligar:
> `make streaming-parar`. (O `make derruba`, ao fim da aula, também desliga.)

---

## A prova final

<!-- rodar: shell -->
```bash
make validar
```

```
...
DIMENSIONAL (DW)
  ✅ modelagem igual ao modelo (04_dw_evoluido.dbml) (11 tabelas, 15 FKs)
  (comparando o DW com a fotografia que o ETL tirou do transacional)
  ✅ dim_tempo cobre todas as datas de venda (0)
  ✅ dim_localidade tem as 27 UFs (27)
  ✅ dim_produtos: 1 linha por produto (200)
  ✅ dim_dispositivo: 1 linha por aparelho (585)
  ✅ dim_dispositivo encontrou os anéis de fraude (6 aparelhos compartilhados)
  ✅ dim_pessoas: 1 versão ATUAL por pessoa (504)
  ✅ dim_pessoas: 1 versão por endereço (SCD 2) (586)
  ✅ dim_pessoas: versões da mesma pessoa não se sobrepõem (0)
  ✅ fato_pedidos: 1 linha por item de pedido (14982)
  ✅ fato_pedidos: faturamento igual ao do transacional (nada em dobro) (95236486.25)
  ✅ fato_pedidos: mesmas fraudes do transacional (236)
  ✅ fato_entregas: 1 linha por pedido embarcado (4641)
  ✅ fato_entregas: o rateio do frete fecha com o que foi pago (fato 1085491.78 x transacional 1085490.55; a diferença é arredondamento)
  ✅ fato_ciclo_pedido: 1 linha por pedido (5003)
  ✅ fato_ciclo_pedido: status igual ao do transacional (0)
  ✅ fato_peso_diario: o agregado fecha com a fato_entregas (204866850)

41 passaram, 0 falharam
```

O validador compara o DW com a fotografia que o ETL tirou. **41 passaram, 0
falharam** quer dizer: nada se perdeu e nada foi contado em dobro na
transformação.

---

## As três demandas, respondidas

| Demanda | A pergunta | Onde está a resposta |
|---|---|---|
| 1. Antifraude | Onde a fraude acontece? | Passo 09, prova 2: 100% das compras de fora de SP, MG e RJ |
| 1. Antifraude | Quais aparelhos são usados por várias contas? | Passo 07: `WHERE is_compartilhado` |
| 2. Logística | Qual transportadora atrasa? | Passo 10, prova 2: Barato Fretes, 42% |
| 2. Logística | Qual o peso médio transportado? | Passo 12, prova 2: cerca de 44 kg por pedido |
| 3. Operações | Onde o pedido trava? | Passo 11: do pagamento ao envio são 40 horas |

Nenhuma dessas perguntas tinha resposta na etapa 1. Falta mostrar isso a quem
decide.

---

## 🆘 Se algo deu errado

| O que apareceu | O que é | O que fazer |
|---|---|---|
| `❌ Modelagem do DIMENSIONAL (DW) incompleta` | A etapa 6 não terminou | Corrija o que a lista aponta, ou `make gabarito-dw` |
| `ERROR: relation "stg.pedidos" does not exist` | Você pulou o passo 01 | Rode os passos na ordem, ou `make etl` |
| `ERROR: schema "oltp" does not exist` | Você pulou o passo 00 | `make etl-passo p=00` |
| `ERROR: could not connect to server "servidor_oltp"` | O container do transacional está parado | `make subir` |
| `ERROR: null value in column "..." violates not-null constraint` | Sobrou uma coluna `NOT NULL` do legado na fato | `make conferir-dw` mostra qual; remova com `DROP COLUMN` |
| A prova 1 do passo 09 não bate | A fato tem linhas de uma carga antiga | No DW: `TRUNCATE fato_pedidos;` e rode `make etl` |

Mais em [docs/faq.md](../docs/faq.md).

---

## ✅ Antes de seguir

* [ ] Rodei os 13 passos e li a prova de cada um
* [ ] Vi o Ravi Rios com duas linhas em `dim_pessoas`
* [ ] A soma de `fato_pedidos` é **igual** à soma dos pedidos do transacional
* [ ] `make etl` pela segunda vez mostrou `MERGE 0`
* [ ] Com o streaming ligado, o ETL atualizou só o que mudou
* [ ] `make validar` mostra **0 falharam**

---

# ➡️ Continue em [dashboard/README.md](../dashboard/README.md)
