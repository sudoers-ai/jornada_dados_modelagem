-- ==========================================================================
-- ETL - passo 09 - fato_pedidos: a FATO TRANSACIONAL
--
-- GRAO: uma linha por ITEM de pedido (pedido x produto).
-- O grao e a decisao mais importante de uma fato. Toda MEDIDA dentro dela
-- tem que estar nesse mesmo grao - senao a soma mente.
--
-- Foi exatamente esse o erro do DW legado: a coluna `total` guardava o
-- valor do PEDIDO INTEIRO, repetido em cada item. Um pedido de R$ 300 com
-- 3 itens somava R$ 900. Aqui a medida e `valor_total` do ITEM: somar
-- todas as linhas de um pedido da o valor do pedido, sem contar dobrado.
--
-- O que este passo faz com o dado do transacional:
--   - 5 tabelas (pedidos, itens, auditoria, produtos, pagamentos) viram 1;
--   - cada id de origem e TROCADO pela sk_ da dimensao correspondente;
--   - a pessoa e ligada a VERSAO dela que valia no dia da venda (SCD 2);
--   - nascem medidas que nao existiam: preco unitario e peso do item.
-- ==========================================================================
MERGE INTO fato_pedidos AS f
USING (
    SELECT p.id                                   AS id_pedido,
           i.id_produto,
           to_char(p.dt_venda, 'YYYYMMDD')::integer AS sk_tempo,
           dpe.sk_pessoa,
           dpr.sk_produto,
           ddi.sk_dispositivo,
           dlo.sk_localidade,
           dfp.sk_forma_pagamento,
           a.geohash,
           p.dt_venda,
           i.qtde,
           round(i.valor_total / i.qtde, 2)       AS valor_unit,    -- preco NO DIA da venda
           i.valor_total,                                           -- valor do ITEM
           i.qtde * pr.peso_gramas                AS peso_gramas,   -- medida nova
           p.status,
           a.is_fraude,
           a.motivo_fraude
    FROM stg.pedidos p
    JOIN stg.itens_pedidos     i   ON i.id_pedido = p.id
    JOIN stg.auditoria_pedidos a   ON a.id_pedido = p.id
    JOIN stg.produtos          pr  ON pr.id = i.id_produto
    JOIN (  -- o pagamento mais recente de cada pedido
            SELECT DISTINCT ON (id_pedido) id_pedido, forma
            FROM stg.pagamentos ORDER BY id_pedido, id DESC
         )                     g   ON g.id_pedido = p.id
    -- troca dos ids de origem pelas chaves substitutas:
    JOIN dim_produtos          dpr ON dpr.id = i.id_produto
    JOIN dim_dispositivo       ddi ON ddi.device_id = a.device_id
    JOIN dim_localidade        dlo ON dlo.uf = a.uf
    JOIN dim_forma_pagamento   dfp ON dfp.forma = g.forma
    JOIN dim_pessoas           dpe ON dpe.id = p.id_pessoa
                                  -- a versao da pessoa valida NA DATA da venda:
                                  AND p.dt_venda >= dpe.dt_inicio
                                  AND p.dt_venda <  COALESCE(dpe.dt_fim, 'infinity')
) AS o
ON f.id_pedido = o.id_pedido AND f.id_produto = o.id_produto
-- o pedido ja estava na fato e algo mudou (status avancou, fraude confirmada):
WHEN MATCHED AND (f.status, f.is_fraude, f.motivo_fraude, f.sk_forma_pagamento)
                 IS DISTINCT FROM (o.status, o.is_fraude, o.motivo_fraude, o.sk_forma_pagamento) THEN
    UPDATE SET status             = o.status,
               is_fraude          = o.is_fraude,
               motivo_fraude      = o.motivo_fraude,
               sk_forma_pagamento = o.sk_forma_pagamento
WHEN NOT MATCHED THEN
    INSERT (id_pedido, id_produto, sk_tempo, sk_pessoa, sk_produto, sk_dispositivo,
            sk_localidade, sk_forma_pagamento, geohash, dt_venda, qtde, valor_unit,
            valor_total, peso_gramas, status, is_fraude, motivo_fraude)
    VALUES (o.id_pedido, o.id_produto, o.sk_tempo, o.sk_pessoa, o.sk_produto, o.sk_dispositivo,
            o.sk_localidade, o.sk_forma_pagamento, o.geohash, o.dt_venda, o.qtde, o.valor_unit,
            o.valor_total, o.peso_gramas, o.status, o.is_fraude, o.motivo_fraude);

\echo ''
\echo '--- prova 1: a soma da fato BATE com o transacional (nada contado em dobro)'
SELECT (SELECT sum(valor_total) FROM fato_pedidos)      AS soma_na_fato,
       (SELECT sum(valor_total) FROM stg.pedidos)       AS soma_dos_pedidos_no_oltp,
       (SELECT count(*) FROM fato_pedidos)              AS linhas_na_fato,
       (SELECT count(*) FROM stg.itens_pedidos)         AS itens_no_oltp;

\echo '--- prova 2: taxa de fraude por UF, em 1 JOIN (no transacional seriam 3)'
SELECT l.uf, l.is_area_atendida,
       count(DISTINCT f.id_pedido)                                   AS pedidos,
       count(DISTINCT f.id_pedido) FILTER (WHERE f.is_fraude)        AS fraudes,
       round(100.0 * count(DISTINCT f.id_pedido) FILTER (WHERE f.is_fraude)
             / count(DISTINCT f.id_pedido), 1)                       AS pct_fraude
FROM fato_pedidos f
JOIN dim_localidade l ON l.sk_localidade = f.sk_localidade
GROUP BY l.uf, l.is_area_atendida
ORDER BY pedidos DESC;
