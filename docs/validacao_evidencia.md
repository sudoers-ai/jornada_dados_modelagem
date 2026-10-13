# 🔎 Guia de validação por evidências

> ⬅️ [README principal](../README.md)

"Rodou sem erro" não é evidência. Evidência é um **resultado que você
consegue mostrar** e que só existe se a etapa deu certo. Este guia diz, para
cada etapa, qual é esse resultado e como obtê-lo.

Regra geral: nesta disciplina toda etapa tem um **comando de prova** que
termina com ✅ ou diz o que falta.

| Etapa | Comando de prova | Evidência de sucesso |
|---|---|---|
| 0 | `make status` | 4 containers `healthy` |
| 3 | `make conferir-oltp` | `13 tabelas, 90 colunas, 13 FKs, 0 pendências` |
| 4 | `make historico` | `✅ Histórico carregado com sucesso` |
| 4 | `make streaming ciclos=5` | `✅ Streaming concluído: 5 ciclos sem erro` |
| 4 | `make validar` | `25 passaram, 0 falharam` |
| 6 | `make conferir-dw` | `11 tabelas, 110 colunas, 15 FKs, 0 pendências` |
| 7 | `make etl` | `✅ ETL concluido.` |
| 7 | `make validar` | `41 passaram, 0 falharam` |
| 8 | `make conferir-dashboards` | `✅ Dashboards conferidos` |

---

## 0) Ambiente

```bash
make status
```

Os quatro containers com `(healthy)`. Se o Metabase estiver `(health:
starting)`, espere um minuto e rode de novo.

Evidência complementar: http://localhost:3020 abre a tela de login.

## 1) O legado

```bash
docker exec modelagem_oltp psql -U sudoers -d liga_sudoers -c "\dt"
docker exec modelagem_dw   psql -U sudoers -d liga_sudoers_dw -c "\dt"
```

6 tabelas em cada banco.

## 3) O transacional evoluído

```bash
make conferir-oltp
```

```
✅ Modelagem do TRANSACIONAL (OLTP) conferida: 13 tabelas, 90 colunas, 13 FKs, 0 pendências.
```

O que essa linha garante: todas as tabelas e colunas do modelo existem, com o
tipo certo, a obrigatoriedade certa, os valores padrão, as chaves primárias,
as chaves únicas, as 13 chaves estrangeiras e o trigger de `updated_at` em
cada tabela.

Evidência complementar (a chave estrangeira funcionando):

```bash
docker exec modelagem_oltp psql -U sudoers -d liga_sudoers -c \
  "INSERT INTO status_pedidos (id_pedido, status, dt_evento) VALUES (999999, 'pago', now());"
```

Tem que dar `ERROR: ... violates foreign key constraint`.

## 4) Os dados

```bash
make validar
```

O validador gera o universo de novo em memória e compara com o banco, tabela
por tabela. Depois confere a coerência entre as tabelas novas e as antigas:

| Verificação | O que prova |
|---|---|
| `pedidos tem as linhas do gerador (5000)` | o histórico entrou inteiro |
| `todo pedido tem pagamento` | a tabela nova está ligada à antiga |
| `o status do pedido é o último evento do histórico de status` | `pedidos.status` e `status_pedidos` contam a mesma história |
| `o valor do pedido é a soma dos itens` | integridade dos valores |
| `toda pessoa tem exatamente 1 endereço principal` | a regra de mudança de endereço se sustenta |
| `pedido enviado ou entregue está em algum transporte` | a relação N:N está coerente |

Depois que o streaming roda, as contagens deixam de ser exatas e o validador
passa a conferir **mínimos** ("pelo menos as linhas do histórico"). As
verificações de coerência continuam valendo.

Evidência de que o streaming faz `UPDATE` (e que o trigger funciona):

```bash
docker exec modelagem_oltp psql -U sudoers -d liga_sudoers -c \
  "SELECT id_pedido, is_fraude, motivo_fraude, dt_fraude, updated_at
   FROM auditoria_pedidos WHERE id_pedido > 5000 AND is_fraude LIMIT 3;"
```

## 5) O problema do legado

```bash
docker exec modelagem_dw psql -U sudoers -d liga_sudoers_dw -c \
  "SELECT (SELECT sum(total) FROM fato_pedidos) AS no_dashboard,
          (SELECT sum(valor_total) FROM oltp.pedidos) AS de_verdade;"
```

Dois números diferentes, o primeiro quase 4 vezes maior. (Só funciona antes
da etapa 6: depois, a coluna `total` não existe mais.)

## 6) O dimensional evoluído

```bash
make conferir-dw
```

```
✅ Modelagem do DIMENSIONAL (DW) conferida: 11 tabelas, 110 colunas, 15 FKs, 0 pendências.
```

## 7) O ETL

Cada passo imprime a própria prova. As quatro mais importantes:

| Passo | Prova | O que tem que acontecer |
|---|---|---|
| 08 | `linhas_na_dimensao` × `pessoas` | Mais linhas do que pessoas (SCD tipo 2) |
| 09 | `soma_na_fato` × `soma_dos_pedidos_no_oltp` | **Idênticas** |
| 10 | `frete_na_fato` × `frete_no_oltp` | Diferença de centavos (arredondamento) |
| 12 | `peso_no_agregado` × `peso_na_fato_entregas` | **Idênticos** |

E o conjunto:

```bash
make validar
```

`41 passaram, 0 falharam`. A parte do DW compara cada tabela com a fotografia
(schema `stg`) que o ETL tirou do transacional.

Evidência de idempotência:

```bash
make etl | grep -E "MERGE|INSERT|UPDATE"
```

Rodado duas vezes seguidas com o streaming desligado, a segunda mostra
`MERGE 0` em todas as dimensões e fatos.

## 8) Os dashboards

```bash
make conferir-dashboards
```

```
✅ Dashboards conferidos: 30 gráficos rodando, antigos consertados, 3 dashboards novos no ar.
```

O comando roda cada gráfico pela API do Metabase, lê o SQL dos gráficos
antigos para ver se o erro original ainda está lá, e confere se os três
dashboards novos existem com a quantidade de gráficos do roteiro.

Evidência complementar: um *print* de cada um dos cinco dashboards.

---

## Para entregar

Um bom relatório de evidências tem, para cada etapa:

1. o comando de prova e a saída dele;
2. uma frase dizendo **o que aquela saída prova**;
3. (opcional) um *print* de tela.

A frase do item 2 é o que diferencia quem executou de quem entendeu.
