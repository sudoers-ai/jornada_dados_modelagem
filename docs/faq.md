# ❓ FAQ de aula — erros comuns e soluções

> ⬅️ [README principal](../README.md)

Antes de qualquer coisa, dois comandos resolvem ou explicam a maioria dos
problemas:

```bash
make status         # os 4 containers estão healthy?
make diagnostico    # relatório completo para mandar ao instrutor
```

---

## Subindo o ambiente

### `make verificar` diz que uma porta está ocupada

Outro programa da sua máquina está usando a porta. Abra o arquivo `.env`, na
raiz do repositório, e troque o número indicado na mensagem:

```bash
PORTA_OLTP=5540        # era 5440
```

Rode `make verificar` de novo e depois `make subir`. Se você trocar a
`PORTA_METABASE`, o endereço do Metabase passa a ser
`http://localhost:<nova porta>`.

### `docker: 'compose' is not a docker command`

Você tem o Compose antigo (v1). Instale o plugin novo:

```bash
sudo apt update && sudo apt install docker-compose-plugin
docker compose version
```

### `permission denied while trying to connect to the Docker daemon`

O seu usuário não está no grupo `docker`:

```bash
sudo usermod -aG docker $USER
```

Feche a sessão e entre de novo (ou reinicie) para valer.

### Estou no Windows e nada funciona

Quase sempre é uma destas três coisas: o comando foi digitado no PowerShell
em vez do terminal do **Ubuntu (WSL)**; o Docker Desktop está fechado; ou o
repositório foi clonado numa pasta do Windows (`/mnt/c/...`). O guia
[Preparando o Windows](./windows.md) tem o passo a passo e uma tabela só de
problemas do Windows.

### `make: command not found`

O `make` é pré-requisito da trilha e não vem com o Docker. Instale:

| Sistema | Como instalar |
|---|---|
| Windows | no terminal do **Ubuntu (WSL)**: `sudo apt update && sudo apt install make`. Veja [Preparando o Windows](./windows.md) |
| Ubuntu / Debian | `sudo apt update && sudo apt install make` |
| Fedora | `sudo dnf install make` |
| Mac | `xcode-select --install` |

Confira com `make --version` e rode o comando de novo.

No Windows, se você já instalou e o erro continua, é porque está no
PowerShell ou no Prompt de Comando: eles não enxergam o `make` do WSL, e os
scripts do repositório são `bash`.

### O Metabase fica em `health: starting` e não abre

Ele leva de 1 a 2 minutos para subir, mais numa máquina com pouca memória.
Acompanhe:

```bash
make logs s=metabase
```

Procure a linha `Metabase Initialization COMPLETE`. Se ela não aparecer em 5
minutos, a causa quase sempre é memória. Feche outros programas e rode
`make consertar`.

* **No Mac:** dê pelo menos 4 GB ao Docker em Docker Desktop → Settings →
  Resources.
* **No Windows:** quem define a memória é o WSL, que por padrão pode usar até
  metade da RAM do computador. Não há o que ajustar no Docker Desktop.

### Subi, derrubei e os dados sumiram

`make derruba` **mantém** os dados. `make limpar` **apaga**. Se você rodou
`docker compose down -v` na mão, o `-v` apagou os volumes.

### Quero recomeçar do zero

```bash
make limpar
make subir
```

---

## Etapa 3 — Evoluir o transacional

### `ERROR: relation "dispositivos" does not exist`

Você tentou criar uma chave estrangeira para uma tabela que ainda não existe.
A ordem dos blocos importa: rode-os na sequência do roteiro.

### `ERROR: function update_updated_at_column() does not exist`

Você está no banco errado. Essa função só existe no transacional. Saia
(`\q`) e entre com `make psql-oltp`. O prompt certo é `liga_sudoers=#` (o do
DW é `liga_sudoers_dw=#`).

### O `psql` mostra `liga_sudoers-#` ou `liga_sudoers(#` e não responde

Ficou um comando pela metade: faltou um `;` ou um `)`. Aperte `Ctrl+C` para
descartar e cole o bloco inteiro de novo.

### `ERROR: column "x" of relation "y" already exists`

Você já tinha criado essa coluna. Os blocos do roteiro usam `IF NOT EXISTS`
justamente para isso não acontecer; se você digitou sem o `IF NOT EXISTS`,
pode ignorar o erro.

### A conferência diz "tipo esperado inteiro, encontrado texto" (ou parecido)

Uma coluna foi criada com o tipo diferente do modelo. O jeito mais simples é
apagar e recriar só ela:

```sql
ALTER TABLE nome_da_tabela DROP COLUMN nome_da_coluna;
```

Depois cole de novo o bloco do roteiro que cria essa coluna.

### A conferência diz "não deveria ser NOT NULL"

Você colocou `NOT NULL` numa coluna que o modelo deixa aceitar nulo (como
`transportes.dt_entrega`). Conserte assim:

```sql
ALTER TABLE nome_da_tabela ALTER COLUMN nome_da_coluna DROP NOT NULL;
```

### A conferência diz "falta o trigger que atualiza o updated_at"

Faltou o `CREATE OR REPLACE TRIGGER ...` daquela tabela. Ele está no mesmo
bloco do `CREATE TABLE`, logo abaixo.

### Rodei `make gabarito-oltp` e ainda há pendências

O gabarito só **acrescenta** o que falta (tabela, coluna, chave estrangeira,
trigger). Ele não desfaz uma coluna que você criou com o tipo errado, com
`NOT NULL` a mais ou sem `DEFAULT`. Corrija as linhas que sobraram na lista
(as três perguntas acima mostram como) ou recomece do zero:

```bash
make reset-oltp && make gabarito-oltp && make historico
```

### Baguncei tudo

```bash
make reset-oltp       # volta às 6 tabelas do legado (apaga os pedidos)
```

E refaça a etapa 3. Ou, para ir direto à resposta: `make gabarito-oltp`.

---

## Etapa 4 — Histórico e streaming

### `❌ Modelagem do TRANSACIONAL (OLTP) incompleta`

É o portão funcionando: a etapa 3 não terminou. A lista diz exatamente o que
falta.

### `❌ O banco recusou a carga. Nada foi gravado.`

O seu banco tem uma restrição que o modelo não tem: um `CHECK`, um `UNIQUE` a
mais, um `varchar` menor que o do modelo. A mensagem mostra o erro do
PostgreSQL com o nome da tabela. Corrija a restrição ou, na dúvida:

```bash
make reset-oltp && make gabarito-oltp && make historico
```

### `✅ O histórico já está carregado. Nada foi alterado.`

Não é erro. O script não duplica dados. Para apagar e gerar de novo:

```bash
make historico args=--limpar
```

### As minhas contagens não batem com as do roteiro

* Depois do `make historico`, as contagens são **idênticas** para todo mundo
  (5000 pedidos, 14976 itens...). Se as suas diferem, você alterou `SEMENTE`
  ou `N_PEDIDOS` no `.env`.
* Depois do **streaming**, os números passam a variar: ele sorteia o que
  acontece. É esperado.

### O streaming mostra muitos ciclos "sem novidades"

É de propósito. O histórico tem cerca de 28 pedidos por dia; se o streaming
criasse vários pedidos a cada 5 segundos, em meia hora o "hoje" teria mais
vendas que o mês inteiro e os gráficos ficariam distorcidos. O primeiro ciclo
força um acontecimento de cada tipo; os seguintes seguem um ritmo de operação
normal.

### Deixei o streaming ligado por horas e os gráficos de "hoje" ficaram enormes

O streaming acelera o tempo, mesmo no ritmo reduzido. Para voltar ao estado
inicial:

```bash
make streaming-parar
make historico args=--limpar
make etl
```

### Como paro o streaming?

Se está no terminal: `Ctrl+C`. Se está em segundo plano:
`make streaming-parar`.

---

## Etapas 5 a 7 — O DW e o ETL

### `ERROR: relation "stg_pessoas" does not exist` no `make etl-legado`

O ETL antigo só funciona **antes** da etapa 6: depois dela, as tabelas `stg_*`
foram removidas e a fato mudou de forma. Se você quer rever a etapa 5,
`make reset-dw` volta o DW ao legado (e você terá que refazer a etapa 6).

### `ERROR: column "dt_inicio" of relation "dim_pessoas" contains null values`

A tabela tinha dado quando você tentou criar uma coluna `NOT NULL` sem valor
padrão. Rode primeiro o bloco 6.1 (o `TRUNCATE`) e depois o 6.3.

### `ERROR: cannot truncate a table referenced in a foreign key constraint`

Faltou o `CASCADE` no fim do `TRUNCATE`. Cole o bloco 6.1 inteiro.

### `❌ Modelagem do DIMENSIONAL (DW) incompleta` ao rodar `make etl`

O portão do DW: a etapa 6 não terminou.

### `ERROR: could not connect to server "servidor_oltp"`

O container do transacional está parado. `make subir`.

### `ERROR: schema "stg" does not exist` (ou `"oltp"`)

Você rodou um passo do ETL sem os anteriores. Rode na ordem
(`make etl-passo p=00`, depois `p=01`...) ou tudo de uma vez com `make etl`.

### A prova do passo 09 não bate (soma da fato ≠ soma do transacional)

A fato tem linhas de uma carga antiga. No `psql` do DW:

```sql
TRUNCATE fato_pedidos;
```

E rode `make etl`.

### Rodei `make etl` de novo e o `MERGE` não deu zero

Se o streaming está ligado, é esperado: entrou dado novo. Com o streaming
desligado e duas rodadas seguidas, tem que dar zero (menos a
`fato_peso_diario`, que é sempre refeita).

### `make validar` falhou em um item do DW

A mensagem mostra o valor esperado e o encontrado. Quase sempre é porque o
ETL não rodou até o fim, ou porque o streaming gravou algo entre a foto do
ETL e a validação — nesse caso, rode `make etl` e `make validar` em seguida.

---

## Etapa 8 — Dashboards

### Não consigo entrar no Metabase

E-mail `contato@sudoers.com.br`, senha `*liga01` (com o asterisco). O
endereço é http://localhost:3020, a menos que você tenha trocado a
`PORTA_METABASE`.

### A tabela ou a coluna nova não aparece no Metabase

O Metabase não relê o banco sozinho na hora. Rode `make metabase-sync`.

### `ERROR: relation "fato_ciclo_pedido" does not exist` ao executar um gráfico

O editor está apontando para o banco errado. O Metabase abre o editor no
último banco usado. Troque para **Liga DW** no canto superior esquerdo.

### Consertei o gráfico e ele continua quebrado no dashboard

Ao salvar, você escolheu "Salvar como uma nova pergunta". O dashboard ainda
aponta para a antiga. Abra o link direto do gráfico de novo, cole o SQL e, ao
salvar, escolha **Substituir a pergunta original**.

### Não acho o botão ABRIR EDITOR

Você abriu um gráfico que não é escrito em SQL. Alguns gráficos do dashboard
são construídos **em cima** de outro (o de linha do faturamento, a pizza de
categorias, os números de vendas e ticket médio). Conserte o gráfico de
origem, usando o link direto que o roteiro dá.

### Os dashboards do DW não atualizam com o streaming

É assim mesmo: eles leem o DW, que só muda quando o ETL roda. Rode `make etl`
e atualize a página. O dashboard **Transacional** é o único que muda sozinho.

### Estraguei os dashboards

`make gabarito-dashboards` conserta os gráficos antigos e recria os novos.
Para voltar o Metabase inteiro ao estado inicial, só com `make limpar` (que
apaga também os bancos).

---

## Geral

### Posso usar DBeaver, pgAdmin ou outro cliente?

Pode. Os bancos estão publicados na sua máquina:

| Banco | Host | Porta | Database | Usuário | Senha |
|---|---|---|---|---|---|
| Transacional | `localhost` | `5440` | `liga_sudoers` | `sudoers` | `password` |
| Dimensional | `localhost` | `5441` | `liga_sudoers_dw` | `sudoers` | `password` |

### Este repositório precisa dos outros da Jornada?

Não. Ele é autocontido. A pasta [`integracao/`](../integracao/README.md)
mostra como ligá-lo aos outros, e é opcional.

### Onde vejo o modelo como diagrama?

Cole o conteúdo de qualquer arquivo de `modelagem/dbml/` em
[dbdiagram.io/d](https://dbdiagram.io/d). As mesmas imagens estão em
`modelagem/img/`.

### Como peço ajuda?

Rode `make diagnostico`, copie a saída inteira e mande ao instrutor junto com
a etapa em que você está.
