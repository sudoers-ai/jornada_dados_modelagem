# ✅ Checklist do aluno

> ⬅️ [README principal](../README.md)

Use este checklist para não se perder entre as etapas. Marque cada item
**somente depois de ver a evidência** correspondente. O detalhe de cada
evidência está em [validacao_evidencia.md](./validacao_evidencia.md).

### 0) Preparação do ambiente

* [ ] **Windows:** segui o guia [Preparando o Windows](./windows.md) e estou no terminal do Ubuntu (WSL)
* [ ] Docker e Docker Compose v2 instalados
* [ ] `make --version` mostra a versão do `make`
* [ ] `make verificar` terminou com **Tudo certo**
* [ ] `make subir` terminou com **Tudo no ar**
* [ ] `make status` mostra os 4 containers `healthy`

### 1) Conhecer o legado

* [ ] Listei as 6 tabelas do transacional (`\dt`)
* [ ] Contei 12 categorias, 200 produtos, 500 pessoas e 0 pedidos
* [ ] Listei as 6 tabelas do DW
* [ ] Entrei no Metabase e abri os dashboards **Transacional** e **Datawehoure**
* [ ] Sei dizer por que nenhuma das três demandas tem resposta hoje

### 2) As três demandas

* [ ] Abri o `02_oltp_evoluido.dbml` no dbdiagram.io
* [ ] Sei a diferença entre `dispositivo` e `device_id`
* [ ] Sei por que `enderecos` e `carga_pedidos` são tabelas
* [ ] Sei ler `pk`, `not null`, `default` e `Ref:` no modelo

### 3) Evoluir o transacional

* [ ] Demanda 1 aplicada: `make conferir-oltp` caiu de 15 para 9 pendências
* [ ] Demanda 2 aplicada: caiu para 3
* [ ] Demanda 3 aplicada: **0 pendências**
* [ ] `\dt` lista 13 tabelas
* [ ] Vi a chave estrangeira recusar um `INSERT` inválido

### 4) Histórico e streaming

* [ ] `make historico` terminou com **Histórico carregado com sucesso**
* [ ] Contagens conferidas: 5000 pedidos, 14976 itens, 590 transportes, 234 fraudes
* [ ] `make validar`: **25 passaram, 0 falharam**
* [ ] `make streaming ciclos=5` terminou com **Streaming concluído**
* [ ] Vi o pedido 1 por inteiro e os 6 anéis de fraude
* [ ] Anotei "Qtde vendas" e "Ticket médio" do dashboard Transacional

### 5) O DW de hoje

* [ ] `make etl-legado` carregou o DW antigo
* [ ] Vi o dashboard **Datawehoure** com dados
* [ ] Reproduzi o faturamento em dobro (quase 4× o real)
* [ ] Reproduzi a duplicação de vendas do produto 1
* [ ] Sei explicar o que é **grão**

### 6) Evoluir o dimensional

* [ ] Legado esvaziado (`TRUNCATE`) e `stg_*` removidas
* [ ] 7 dimensões criadas ou evoluídas: `make conferir-dw` caiu de 31 para 19
* [ ] 4 fatos criadas ou evoluídas: **0 pendências**
* [ ] Sei dizer o grão de cada uma das 4 fatos
* [ ] Sei por que o preço fica na fato

### 7) O ETL novo

* [ ] Rodei os 13 passos (`make etl-passo p=00` até `p=12`) e li cada prova
* [ ] Vi o Ravi Rios com duas linhas em `dim_pessoas`
* [ ] Soma de `fato_pedidos` **igual** à soma dos pedidos do transacional
* [ ] Segunda rodada do `make etl`: `MERGE 0`
* [ ] Com o streaming ligado, o ETL atualizou só o que mudou
* [ ] `make validar`: **41 passaram, 0 falharam**

### 8) Dashboards

* [ ] `make metabase-sync` rodou
* [ ] Dashboard renomeado para **Data Warehouse**
* [ ] 4 gráficos do DW consertados (faturamento, ticket médio, regiões, churn)
* [ ] 3 gráficos do Transacional consertados (pedidos por data, produtos vendidos, valor por pedido)
* [ ] Gráfico novo "Pedidos por situação" no Transacional
* [ ] Dashboards **Antifraude**, **Logística** e **Ciclo do pedido** criados
* [ ] `make conferir-dashboards`: **Dashboards conferidos**

### 9) Desafios

* [ ] Escolhi o meu nível em [desafios/desafios.md](../desafios/desafios.md)
* [ ] Entregáveis prontos

### Ao fim de cada aula

* [ ] `make derruba` (para os containers e **mantém** o seu progresso)
