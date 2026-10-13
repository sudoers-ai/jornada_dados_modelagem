# 📖 Glossário

> ⬅️ [README principal](../README.md)

Os termos da disciplina, cada um com um exemplo da Liga Sudoers. Para a
explicação completa, veja [Do transacional ao dimensional](./modelagem.md).

| Termo | Em uma frase | Na Liga Sudoers |
|---|---|---|
| **OLTP** | Banco desenhado para **gravar** uma operação de cada vez, sem errar | O banco `liga_sudoers`, onde o site grava os pedidos |
| **OLAP / DW** | Banco desenhado para **ler** muito dado de uma vez e responder perguntas | O banco `liga_sudoers_dw` |
| **Normalização (3FN)** | Cada informação em um lugar só | O nome da categoria só existe em `categorias` |
| **Desnormalização** | Repetir informação de propósito para evitar `JOIN` | `dim_produtos.cat_desc` |
| **Chave primária (PK)** | A coluna (ou colunas) que identifica uma linha | `pedidos.id` |
| **Chave estrangeira (FK)** | Coluna que aponta para a chave de outra tabela; o banco garante que o alvo existe | `pedidos.id_pessoa` → `pessoas.id` |
| **Chave composta** | Chave primária formada por mais de uma coluna | (`id_transporte`, `id_pedido`) em `carga_pedidos` |
| **Tabela associativa** | Tabela que existe só para ligar duas outras numa relação N:N | `carga_pedidos` |
| **Trigger** | Código que o banco roda sozinho quando algo acontece numa tabela | `set_updated_at_...` carimba a hora de cada `UPDATE` |
| **Star schema** | Modelo com uma fato no centro e dimensões em volta | `fato_pedidos` cercada de `dim_*` |
| **Fato** | Tabela do acontecimento: chaves e números | `fato_pedidos` |
| **Dimensão** | Tabela do contexto: quem, o quê, onde, quando | `dim_pessoas` |
| **Medida** | Número que se soma | `valor_total`, `peso_gramas`, `qtde` |
| **Grão** | O que uma linha da fato representa | "um item de um pedido" |
| **Chave substituta (`sk_`)** | Chave gerada pelo DW, independente do `id` da origem | `sk_pessoa` |
| **Chave de negócio** | O identificador que veio do transacional | `dim_pessoas.id` |
| **SCD tipo 1** | Quando o atributo muda, sobrescreve | `dim_produtos` |
| **SCD tipo 2** | Quando o atributo muda, cria uma versão nova com validade | `dim_pessoas` (`dt_inicio`, `dt_fim`, `is_atual`) |
| **Fato transacional** | Uma linha por acontecimento | `fato_pedidos`, `fato_entregas` |
| **Snapshot periódico** | Uma linha por período | `fato_peso_diario` |
| **Snapshot acumulado** | Uma linha por processo, preenchida a cada etapa | `fato_ciclo_pedido` |
| **Dimensão com vários papéis** | A mesma dimensão usada mais de uma vez pela mesma fato | `dim_tempo` como saída e como entrega em `fato_entregas` |
| **Dimensão conformada** | Dimensão compartilhada por várias fatos | `dim_pessoas`, `dim_tempo` |
| **Atributo derivado** | Coluna calculada no ETL, que não existe na origem | `dim_dispositivo.is_compartilhado` |
| **Rateio** | Distribuir um valor de grão mais alto pelas linhas de grão mais fino | O frete do caminhão dividido pelos pedidos |
| **ETL** | *Extract, Transform, Load*: tirar da origem, transformar e gravar no destino | Os 13 arquivos de `etl/sql/` |
| **Staging** | Área de passagem: cópia crua da origem dentro do DW | O schema `stg` |
| **Idempotente** | Pode rodar duas vezes sem mudar o resultado | `make etl` rodado de novo mostra `MERGE 0` |
| **Incremental** | Carga que só mexe no que mudou | `MERGE ... WHEN MATCHED AND ... IS DISTINCT FROM` |
| **`MERGE`** | Comando SQL: atualiza quem mudou e insere quem falta | Passos 04, 05, 07, 09, 10 e 11 do ETL |
| **`postgres_fdw`** | Extensão que faz tabelas de outro servidor aparecerem como locais | O schema `oltp` dentro do DW |
| **DBML** | Linguagem de texto para descrever modelos de dados | Os arquivos de `modelagem/dbml/` |
| **Geohash** | Código de texto que representa uma localização no mapa | `auditoria_pedidos.geohash` |
| **`device_id`** | A "impressão digital" de um aparelho físico | Diferente de `dispositivo`, que é só o modelo |
| **Anel de fraude** | Várias contas diferentes operando do mesmo aparelho | Os 6 aparelhos com `is_compartilhado` |
