-- ==========================================================================
-- ETL - passo 10 - fato_entregas: uma fato NOVA, com outro GRAO
--
-- GRAO: uma linha por PEDIDO embarcado em um TRANSPORTE.
--
-- Por que nao colocar isso na fato_pedidos? Porque o grao e outro. A
-- fato_pedidos tem uma linha por ITEM; a entrega acontece por PEDIDO.
-- Misturar graos numa fato so e o caminho mais curto para somar errado.
-- Processo de negocio diferente = fato diferente.
--
-- Tres ideias de modelagem aparecem aqui:
--
--  1. RATEIO. O frete e pago por CAMINHAO (tabela transportes), mas a fato
--     esta no grao de PEDIDO. O valor e distribuido pelo peso de cada
--     pedido. Somando os pedidos de um caminhao, volta o frete dele.
--
--  2. DIMENSAO COM DOIS PAPEIS. A mesma dim_tempo e usada duas vezes:
--     `sk_tempo_saida` e `sk_tempo_entrega`. Uma dimensao, dois papeis.
--
--  3. MEDIDAS CALCULADAS. `dias_transito`, `dias_atraso` e `is_atrasada`
--     nao existem no transacional: nascem aqui, uma vez, com uma regra so.
-- ==========================================================================
MERGE INTO fato_entregas AS f
USING (
    SELECT c.id_transporte,
           c.id_pedido,
           dtr.sk_transportadora,
           dpe.sk_pessoa,
           dlo.sk_localidade,
           to_char(t.dt_saida,   'YYYYMMDD')::integer AS sk_tempo_saida,
           to_char(t.dt_entrega, 'YYYYMMDD')::integer AS sk_tempo_entrega,
           t.dt_saida,
           t.dt_entrega_prevista,
           t.dt_entrega,
           w.peso_gramas,
           -- rateio do frete do caminhao pelo peso do pedido
           COALESCE(round(t.valor_frete * w.peso_gramas / NULLIF(t.peso_total_gramas, 0), 2), 0)
                                                      AS valor_frete,
           t.dt_entrega::date - t.dt_saida::date      AS dias_transito,
           GREATEST(t.dt_entrega::date - t.dt_entrega_prevista::date, 0) AS dias_atraso,
           t.dt_entrega IS NOT NULL                   AS is_entregue,
           -- entregue depois do prazo, ou ainda na estrada com o prazo vencido
           COALESCE(t.dt_entrega, now()) > t.dt_entrega_prevista AS is_atrasada
    FROM stg.carga_pedidos c
    JOIN stg.transportes   t ON t.id = c.id_transporte
    JOIN stg.pedidos       p ON p.id = c.id_pedido
    JOIN stg.enderecos     e ON e.id = p.id_endereco_entrega
    JOIN (  -- o peso de cada pedido: soma do peso dos itens
            SELECT i.id_pedido, sum(i.qtde * pr.peso_gramas)::integer AS peso_gramas
            FROM stg.itens_pedidos i
            JOIN stg.produtos pr ON pr.id = i.id_produto
            GROUP BY i.id_pedido
         )                 w ON w.id_pedido = c.id_pedido
    JOIN dim_transportadora dtr ON dtr.id = t.id_transportadora
    JOIN dim_localidade     dlo ON dlo.uf = e.uf                -- UF de DESTINO
    JOIN dim_pessoas        dpe ON dpe.id = p.id_pessoa
                               AND p.dt_venda >= dpe.dt_inicio
                               AND p.dt_venda <  COALESCE(dpe.dt_fim, 'infinity')
) AS o
ON f.id_transporte = o.id_transporte AND f.id_pedido = o.id_pedido
-- o caminhao chegou (ou o prazo venceu) depois da ultima carga:
WHEN MATCHED AND (f.dt_entrega, f.is_entregue, f.is_atrasada)
                 IS DISTINCT FROM (o.dt_entrega, o.is_entregue, o.is_atrasada) THEN
    UPDATE SET sk_tempo_entrega = o.sk_tempo_entrega,
               dt_entrega       = o.dt_entrega,
               dias_transito    = o.dias_transito,
               dias_atraso      = o.dias_atraso,
               is_entregue      = o.is_entregue,
               is_atrasada      = o.is_atrasada
WHEN NOT MATCHED THEN
    INSERT (id_transporte, id_pedido, sk_transportadora, sk_pessoa, sk_localidade,
            sk_tempo_saida, sk_tempo_entrega, dt_saida, dt_entrega_prevista, dt_entrega,
            peso_gramas, valor_frete, dias_transito, dias_atraso, is_entregue, is_atrasada)
    VALUES (o.id_transporte, o.id_pedido, o.sk_transportadora, o.sk_pessoa, o.sk_localidade,
            o.sk_tempo_saida, o.sk_tempo_entrega, o.dt_saida, o.dt_entrega_prevista, o.dt_entrega,
            o.peso_gramas, o.valor_frete, o.dias_transito, o.dias_atraso, o.is_entregue, o.is_atrasada);

\echo ''
\echo '--- prova 1: o rateio fecha (a diferenca de centavos e o arredondamento de cada linha)'
SELECT (SELECT sum(valor_frete) FROM fato_entregas)   AS frete_na_fato,
       (SELECT sum(valor_frete) FROM stg.transportes) AS frete_no_oltp,
       (SELECT sum(valor_frete) FROM fato_entregas)
         - (SELECT sum(valor_frete) FROM stg.transportes) AS diferenca,
       (SELECT count(*) FROM fato_entregas)           AS linhas_na_fato,
       (SELECT count(*) FROM stg.carga_pedidos)       AS cargas_no_oltp;

\echo '--- prova 2: a pergunta da Demanda 2 - custo e pontualidade por transportadora'
SELECT t.nome,
       t.custo_por_kg,
       count(*)                                                       AS entregas,
       round(100.0 * count(*) FILTER (WHERE f.is_atrasada) / count(*), 1) AS pct_atrasadas,
       round(avg(f.dias_transito), 1)                                 AS media_dias_transito
FROM fato_entregas f
JOIN dim_transportadora t ON t.sk_transportadora = f.sk_transportadora
GROUP BY t.nome, t.custo_por_kg
ORDER BY t.custo_por_kg;
