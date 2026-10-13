-- ==========================================================================
-- ETL - passo 04 - dim_produtos: DESNORMALIZAR (SCD tipo 1)
--
-- No transacional, produto e categoria sao DUAS tabelas (3a forma normal:
-- o nome da categoria existe num lugar so). Otimo para gravar.
--
-- No dimensional elas viram UMA: o nome da categoria e copiado para dentro
-- de cada produto (`cat_desc`). Repete texto? Repete. E e de proposito:
-- quem analisa filtra por "Eletronicos", nao por `id_categoria = 1`, e nao
-- quer fazer JOIN para isso.
--
-- SCD tipo 1 = quando o produto muda, a linha e SOBRESCRITA. Nao guardamos
-- como ele era antes. Serve quando o passado nao importa (corrigir um nome).
--
-- E o preco? Nao esta aqui de proposito. O preco muda, e o que interessa e
-- o preco NO MOMENTO DA VENDA - por isso ele mora na fato, nao na dimensao.
--
-- MERGE = "compare origem e destino; atualize quem mudou, insira quem falta".
-- ==========================================================================
MERGE INTO dim_produtos AS d
USING (
    SELECT p.id,
           c.descricao AS cat_desc,          -- <- a desnormalizacao
           p.descricao,
           p.peso_gramas,
           p.created_at,
           p.updated_at
    FROM stg.produtos p
    JOIN stg.categorias c ON c.id = p.id_categoria
) AS o
ON d.id = o.id
WHEN MATCHED AND (d.cat_desc, d.descricao, d.peso_gramas)
                 IS DISTINCT FROM (o.cat_desc, o.descricao, o.peso_gramas) THEN
    UPDATE SET cat_desc    = o.cat_desc,
               descricao   = o.descricao,
               peso_gramas = o.peso_gramas,
               updated_at  = o.updated_at
WHEN NOT MATCHED THEN
    INSERT (id, cat_desc, descricao, peso_gramas, created_at, updated_at)
    VALUES (o.id, o.cat_desc, o.descricao, o.peso_gramas, o.created_at, o.updated_at);

\echo ''
\echo '--- prova: a categoria agora esta DENTRO do produto, sem JOIN'
SELECT cat_desc AS categoria, count(*) AS produtos, round(avg(peso_gramas)) AS peso_medio_gramas
FROM dim_produtos GROUP BY cat_desc ORDER BY cat_desc;
