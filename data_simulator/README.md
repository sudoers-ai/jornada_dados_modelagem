# 4️⃣ Histórico e streaming — a prova

> ⬅️ Anterior: [3. Evoluir o transacional](../modelagem/03_evolucao_oltp/README.md) · [README principal](../README.md) · Etapa 4 de 9

Um modelo só está certo quando **dado de verdade cabe nele**. Nesta etapa
você roda dois programas que gravam em todas as tabelas e colunas que você
criou. Eles são a prova da etapa 3:

* se a sua modelagem está igual ao modelo, eles **rodam até o fim**;
* se não está, eles **param antes de gravar** e dizem o que falta.

| Programa | O que simula | O que testa no seu modelo |
|---|---|---|
| `liga_sudoers_historico.py` | 180 dias de operação já acontecida | Tabelas, colunas, tipos, chaves — com `INSERT` em massa |
| `liga_sudoers_streaming.py` | A operação acontecendo agora, sem parar | Tudo de novo, mais `UPDATE`: valores padrão e triggers |

São os mesmos nomes e o mesmo papel dos scripts do repositório
`liga_sudoers`. A diferença é que aqui você **não instala Python**: eles rodam
dentro de um container.

---

## Estrutura desta pasta

```
data_simulator/
├── liga_sudoers_historico.py   gera o histórico e grava no banco
├── liga_sudoers_streaming.py   gera dados continuamente
├── functions.py                funções reutilizadas pelos dois
└── verificador.py              compara o seu banco com o modelo (DBML)
```

---

## 4.1 O histórico

<!-- rodar: shell -->
```bash
make historico
```

Saída esperada:

```
✅ Modelagem do TRANSACIONAL (OLTP) conferida: 13 tabelas, 90 colunas, 13 FKs, 0 pendências.
Gerando o histórico (semente=42, 5000 pedidos)...

  produtos (peso_gramas)        200
  dispositivos                  583
  enderecos                     578
  transportadoras                 5
  pedidos                      5000
  itens_pedidos               14976
  auditoria_pedidos            5000
  pagamentos                   5000
  status_pedidos              24081
  transportes                   590
  carga_pedidos                4629

  pedidos por situação: entregue=4421, cancelado=329, devolvido=128, enviado=80, pago=20, separado=13, criado=9
  fraudes confirmadas : 234 (4.7% dos pedidos)
  período             : 2026-04-16 até 2026-10-13

✅ Histórico carregado com sucesso. Sua modelagem transacional está correta.
```

Leia a saída de cima para baixo:

1. **A primeira linha é o portão.** Antes de gravar qualquer coisa, o script
   conferiu o seu banco contra o modelo.
2. **Os números são os mesmos para todo mundo.** O gerador usa uma semente
   fixa. Se a sua contagem bate com a de cima, o seu modelo recebeu
   exatamente o dado que deveria. (Só o **período** muda: são sempre os
   últimos 180 dias, terminando no dia em que você rodou.)
3. **Repare nos pedidos que não estão `entregue`.** Há pedidos `criado`,
   `pago`, `separado` e `enviado`: é a operação "em andamento" no momento em
   que a foto foi tirada. O streaming vai dar continuidade a eles.

> **E se a modelagem estivesse errada?** O script pararia assim, sem gravar
> nada:
>
> ```
> ❌ Modelagem do TRANSACIONAL (OLTP) incompleta. Corrija antes de continuar:
>
>    transportes.dt_entrega   não deveria ser NOT NULL (o modelo permite nulo)
>    carga_pedidos.id_pedido  falta a chave estrangeira (FK) para pedidos(id)
>
>    2 pendência(s). O modelo de referência é modelagem/dbml/02_oltp_evoluido.dbml
> ```
>
> Nesse caso, corrija o que a mensagem aponta e rode `make historico` de novo.

Rodar `make historico` uma segunda vez não duplica nada: ele avisa que o
histórico já está carregado. Para apagar e gerar de novo, use
`make historico args=--limpar`.

### Confira com o validador

<!-- rodar: shell -->
```bash
make validar
```

```
TRANSACIONAL (OLTP)
  ✅ modelagem igual ao modelo (02_oltp_evoluido.dbml) (13 tabelas, 13 FKs)
  ✅ pessoa id=1 é a mesma do gerador (Thomas Camargo)
  ✅ categorias tem as linhas do gerador (12)
  ✅ produtos tem as linhas do gerador (200)
  ...
  ✅ o status do pedido é o último evento do histórico de status (0)
  ✅ o valor do pedido é a soma dos itens (0)
  ✅ toda pessoa tem exatamente 1 endereço principal (0)
  ✅ pedido enviado ou entregue está em algum transporte (0)
  ✅ fraude confirmada tem motivo e data (0)

DIMENSIONAL (DW)
  ⏭  pulado: o DW ainda não está na modelagem nova (31 pendências). Isso é esperado até a etapa 6.

25 passaram, 0 falharam
```

O `make validar` é o seu **guia de evidências**. Ele não confere só a
quantidade de linhas: confere se as tabelas novas e as antigas **contam a
mesma história** (o status do pedido bate com o último evento? todo pedido
enviado está num caminhão?). Você vai rodá-lo de novo depois do ETL.

---

## 4.2 Veja o que entrou

Abra o `psql` (`make psql-oltp`) e explore. Estas consultas mostram o modelo
novo trabalhando.

**Um pedido, visto por inteiro.** Antes, de um pedido só se sabia a data e o
valor. Agora:

<!-- rodar: oltp -->
```sql
SELECT p.id, p.dt_venda::date AS venda, p.valor_total, p.status,
       e.cidade, e.uf, g.forma, g.parcelas, g.status AS pagamento
FROM pedidos p
JOIN enderecos e  ON e.id = p.id_endereco_entrega
JOIN pagamentos g ON g.id_pedido = p.id
WHERE p.id = 1;
```

```
 id |   venda    | valor_total |  status  |  cidade  | uf | forma  | parcelas | pagamento
----+------------+-------------+----------+----------+----+--------+----------+-----------
  1 | 2026-09-13 |    10140.44 | entregue | Caldeira | SP | boleto |        1 | aprovado
(1 row)
```

**O ciclo de vida desse pedido** (Demanda 3):

<!-- rodar: oltp -->
```sql
SELECT status, dt_evento
FROM status_pedidos
WHERE id_pedido = 1
ORDER BY dt_evento;
```

```
  status  |         dt_evento
----------+----------------------------
 criado   | 2026-09-13 10:38:03
 pago     | 2026-09-15 19:54:29.816135
 separado | 2026-09-16 01:44:58.079735
 enviado  | 2026-09-16 15:30:36
 entregue | 2026-09-17 20:10:38.6652
(5 rows)
```

Cinco linhas para um pedido. É o boleto que demorou dois dias para ser pago.
(As suas datas serão outras, mas os intervalos entre elas são os mesmos.)

**Em qual caminhão ele foi** (Demanda 2):

<!-- rodar: oltp -->
```sql
SELECT t.id AS transporte, tr.nome AS transportadora, t.placa,
       t.dt_saida::date AS saida, t.dt_entrega_prevista::date AS prevista,
       t.dt_entrega::date AS entrega
FROM carga_pedidos c
JOIN transportes t      ON t.id = c.id_transporte
JOIN transportadoras tr ON tr.id = t.id_transportadora
WHERE c.id_pedido = 1;
```

```
 transporte | transportadora |  placa  |   saida    |  prevista  |  entrega
------------+----------------+---------+------------+------------+------------
        503 | Barato Fretes  | VLA9K78 | 2026-09-16 | 2026-09-18 | 2026-09-17
(1 row)
```

**Uma pessoa que se mudou.** O endereço antigo não foi apagado:

<!-- rodar: oltp -->
```sql
SELECT e.id, e.id_pessoa, p.nome, e.cidade, e.uf, e.is_principal,
       e.created_at::date AS desde
FROM enderecos e
JOIN pessoas p ON p.id = e.id_pessoa
WHERE e.id_pessoa = 7
ORDER BY e.id;
```

```
 id | id_pessoa |   nome    |       cidade       | uf | is_principal |   desde
----+-----------+-----------+--------------------+----+--------------+------------
  7 |         7 | Ravi Rios | Barbosa das Pedras | MG | f            | 2025-03-27
  8 |         7 | Ravi Rios | Souza              | MG | t            | 2026-08-13
(2 rows)
```

Guarde o nome do **Ravi Rios**. Ele reaparece na etapa 7, quando você tiver
que decidir a qual cidade pertencem as compras que ele fez **antes** de se
mudar.

**O anel de fraude** (Demanda 1). A pergunta que era impossível com o
aparelho guardado como texto:

<!-- rodar: oltp -->
```sql
SELECT a.device_id, d.modelo,
       count(DISTINCT p.id_pessoa) AS contas,
       count(*)                    AS pedidos
FROM auditoria_pedidos a
JOIN pedidos p      ON p.id = a.id_pedido
JOIN dispositivos d ON d.device_id = a.device_id
GROUP BY a.device_id, d.modelo
HAVING count(DISTINCT p.id_pessoa) >= 3
ORDER BY contas DESC, pedidos DESC;
```

```
 device_id  |      modelo      | contas | pedidos
------------+------------------+--------+---------
 d-2ad820ca | iPhone 13        |      5 |      21
 d-c891d55d | Pixel 8          |      5 |      20
 d-32df8d45 | Motorola Edge 40 |      5 |      19
 d-3c6841d6 | iPhone 15        |      5 |      18
 d-855b6c5b | iPad Air         |      5 |      18
 d-ca0553a2 | Web Chrome       |      4 |      16
(6 rows)
```

Seis aparelhos, cada um usado por 4 ou 5 contas diferentes. São os seis anéis
de fraude escondidos nos dados. Com `dispositivo = 'iPhone 13'` (o texto),
centenas de clientes legítimos apareceriam juntos. Com `device_id` (a
entidade), só aparecem os fraudadores.

Funciona — mas olhe o tamanho da consulta: três tabelas, um `GROUP BY` e um
`HAVING` para uma pergunta simples. **Guarde esta consulta.** Na etapa 7 a
mesma resposta vai sair de um `WHERE`.

Saia do `psql` com `\q`.

---

## 4.3 O streaming

O histórico só fez `INSERT`. Uma operação viva faz `UPDATE` o tempo todo: o
pagamento é aprovado, o pedido muda de situação, o caminhão chega, a fraude é
confirmada, a pessoa se muda. É o `UPDATE` que testa de verdade os valores
padrão, as chaves e os triggers.

Rode cinco ciclos:

<!-- rodar: shell -->
```bash
make streaming ciclos=5
```

Saída (os acontecimentos são sorteados; os seus serão parecidos, não iguais):

```
✅ Modelagem do TRANSACIONAL (OLTP) conferida: 13 tabelas, 90 colunas, 13 FKs, 0 pendências.
Iniciando geração de dados para Streaming. (5 ciclos)
[18:27:38] ciclo 1 | +1 cliente | +1 pedido(s) (1 suspeito) | 8 pagamento(s) aprovado(s) | 1 recusado(s) | 3 separado(s) | 1 caminhão saiu (7 pedidos) | 1 caminhão chegou (5 pedidos entregues) | 1 devolução
[18:27:43] ciclo 2 | +1 pedido(s) | 1 separado(s) | 1 caminhão saiu (4 pedidos) | pessoa 288 mudou de endereço
[18:27:48] ciclo 3 | 1 separado(s) | fraude confirmada no pedido 5001 (troca_dispositivo) | produto 107 mudou de preço
[18:27:53] ciclo 4 | 1 devolução | pessoa 207 mudou de endereço
[18:27:58] ciclo 5 | 1 pagamento(s) aprovado(s) | 1 separado(s)

✅ Streaming concluído: 5 ciclos sem erro.
   INSERTs e UPDATEs passaram em todas as tabelas novas.
```

Cada ciclo dura 5 segundos. O **primeiro ciclo força um acontecimento de cada
tipo**: é ele que faz deste script uma prova. Os seguintes seguem o ritmo de
uma operação normal, e por isso alguns ciclos não aparecem no log (quando nada
acontece, o script fica em silêncio e avisa de tempos em tempos que continua
vivo).

> **Por que tão devagar?** O histórico tem cerca de 28 pedidos por dia. Se o
> streaming criasse vários pedidos a cada 5 segundos, em meia hora o "hoje"
> teria mais vendas que o mês inteiro, e todos os gráficos da etapa 8 ficariam
> distorcidos.

O que cada acontecimento faz no banco:

| No log | No banco |
|---|---|
| `+1 cliente` | `INSERT` em `pessoas` e `enderecos` |
| `+1 pedido(s)` | `INSERT` em `pedidos`, `itens_pedidos`, `auditoria_pedidos`, `pagamentos`, `status_pedidos` |
| `(1 suspeito)` | um pedido fraudulento entrou — ainda com `is_fraude = false` |
| `pagamento(s) aprovado(s)` | `UPDATE` em `pagamentos` e `pedidos`, `INSERT` em `status_pedidos` |
| `separado(s)` | `UPDATE` em `pedidos`, `INSERT` em `status_pedidos` |
| `caminhão saiu` | `INSERT` em `transportes` e `carga_pedidos`, `UPDATE` em `pedidos` |
| `caminhão chegou` | `UPDATE` em `transportes` (a `dt_entrega` deixa de ser nula) e em `pedidos` |
| `fraude confirmada` | `UPDATE` em `auditoria_pedidos`: `is_fraude`, `motivo_fraude`, `dt_fraude` |
| `mudou de endereço` | `UPDATE` no endereço antigo (`is_principal = false`), `INSERT` do novo |
| `mudou de preço` | `UPDATE` em `produtos` |

### Veja uma fraude sendo confirmada

No `psql` (`make psql-oltp`):

<!-- rodar: oltp -->
```sql
SELECT a.id_pedido, a.uf, a.dispositivo, a.is_fraude, a.motivo_fraude, a.dt_fraude
FROM auditoria_pedidos a
WHERE a.id_pedido > 5000
ORDER BY a.id_pedido
LIMIT 5;
```

```
 id_pedido | uf |     dispositivo      | is_fraude |   motivo_fraude   |         dt_fraude
-----------+----+----------------------+-----------+-------------------+----------------------------
      5001 | SP | Motorola Edge 40     | t         | troca_dispositivo | 2026-10-13 18:27:48.913697
      5002 | MG | Xiaomi Redmi Note 12 | f         |                   |
(2 rows)
```

O pedido 5001 entrou no ciclo 1 como qualquer outro, com `is_fraude = false`.
No ciclo 3 o "analista" confirmou a fraude, e as três colunas foram
preenchidas por um `UPDATE`. (O motivo é sorteado: no seu banco pode ser
`geolocalizacao`, e aí a `uf` será de fora de SP, MG e RJ.)

É por isso que `motivo_fraude` e `dt_fraude` precisavam aceitar nulo, e
`is_fraude` precisava de um `DEFAULT`: a fraude não é conhecida na hora da
compra.

### Veja o trigger de `updated_at` trabalhando

<!-- rodar: oltp -->
```sql
SELECT id, valor_unit, updated_at FROM produtos WHERE id = 1;

UPDATE produtos SET valor_unit = valor_unit WHERE id = 1;

SELECT id, valor_unit, updated_at FROM produtos WHERE id = 1;
```

```
 id | valor_unit |         updated_at
----+------------+----------------------------
  1 |     565.34 | 2026-10-13 18:27:36.127606
(1 row)

UPDATE 1
 id | valor_unit |        updated_at
----+------------+---------------------------
  1 |     565.34 | 2026-10-13 18:27:59.22505
(1 row)
```

(Os horários serão os seus.) O `UPDATE` não mudou o preço (trocou o valor
por ele mesmo) e não mencionou `updated_at`. Mesmo assim o carimbo mudou: foi o trigger. Qualquer `UPDATE`,
vindo de qualquer sistema, deixa o rastro.

Saia do `psql` com `\q`.

---

## 4.4 O primeiro dashboard ganha vida

Abra o Metabase (http://localhost:3020) → **Nossas análises** →
**Transacional**. O dashboard que estava vazio na etapa 1 agora tem dados.

Olhe com atenção dois números e **anote-os**:

* **Qtde vendas nos últimos 7 dias**
* **Ticket médio dos últimos 7 dias**

Eles parecem razoáveis. Estão errados. Você vai descobrir por quê — e
consertar — na etapa 8.

---

## Para saber mais sobre os scripts

**De onde vêm os dados?** De um gerador determinístico em
[`gerador/`](../gerador/). O arquivo `liga_sudoers_gen.py` cria pessoas,
produtos e pedidos; o `extensao_modelagem.py` deriva deles tudo que as três
demandas pedem (endereços, pagamentos, situações, transportes). As regras da
simulação estão no topo do `extensao_modelagem.py`, em português — vale a
leitura.

**Como rodar o streaming sem parar?**

```bash
make streaming            # roda até você apertar Ctrl+C
make streaming-fundo      # roda em segundo plano e devolve o terminal
make streaming-logs       # acompanha o que ele está fazendo
make streaming-parar      # desliga
```

Você vai ligá-lo em segundo plano na etapa 7, para ver o DW reagir.

---

## 🆘 Se algo deu errado

| O que apareceu | O que fazer |
|---|---|
| `❌ Modelagem do TRANSACIONAL (OLTP) incompleta` | A etapa 3 não terminou. Corrija o que a lista aponta, ou rode `make gabarito-oltp` |
| `❌ O banco recusou a carga. Nada foi gravado.` | Existe uma restrição no seu banco que o modelo não tem (um `CHECK`, um `UNIQUE` a mais, um `varchar` menor). A mensagem mostra o erro do PostgreSQL. Na dúvida: `make reset-oltp` e `make gabarito-oltp` |
| `❌ O cadastro base do transacional não é o esperado` | Alguém apagou ou alterou pessoas, produtos ou categorias. `make reset-oltp` e refaça a etapa 3 |
| `❌ Ainda não existe histórico` (no streaming) | Rode `make historico` antes |
| `❌ Não consegui conectar` | Os containers estão parados. `make subir` |

Mais em [docs/faq.md](../docs/faq.md).

---

## ✅ Antes de seguir

* [ ] `make historico` terminou com **✅ Histórico carregado com sucesso**
* [ ] As contagens batem com as deste roteiro (5000 pedidos, 14976 itens, 590 transportes)
* [ ] `make validar` mostra **0 falharam**
* [ ] `make streaming ciclos=5` terminou com **✅ Streaming concluído**
* [ ] Vi o pedido 1 por inteiro e os seis anéis de fraude
* [ ] Abri o dashboard **Transacional** e anotei os dois números

O transacional está pronto e cheio. Agora vamos olhar para o outro lado.

---

# ➡️ Continue em [modelagem/04_dw_legado/README.md](../modelagem/04_dw_legado/README.md)
