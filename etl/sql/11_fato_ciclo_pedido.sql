-- ==========================================================================
-- ETL - passo 11 - fato_ciclo_pedido: SNAPSHOT ACUMULADO
--
-- GRAO: uma linha por PEDIDO - que e ATUALIZADA a cada marco do ciclo.
--
-- No transacional, o ciclo de vida e uma tabela de EVENTOS, na vertical:
--
--     status_pedidos:   pedido 42 | criado   | 10/10 09:00
--                       pedido 42 | pago     | 10/10 09:03
--                       pedido 42 | separado | 10/10 15:00
--                       pedido 42 | enviado  | 11/10 07:00
--
-- Otimo para registrar. Pessimo para perguntar "quanto tempo leva do
-- pagamento ate o envio?": seria preciso juntar a tabela com ela mesma.
--
-- No dimensional, os eventos DEITAM: viram colunas de uma linha so.
--
--     fato_ciclo_pedido: 42 | dt_criado | dt_pago | dt_separado | dt_enviado | dt_entregue
--
-- "Tempo ate o envio" vira uma subtracao entre duas colunas. E a linha vai
-- sendo PREENCHIDA com o tempo: hoje `dt_entregue` esta nula, amanha nao.
-- E o unico tipo de fato em que UPDATE e a regra, nao a excecao.
-- ==========================================================================
MERGE INTO fato_ciclo_pedido AS f
USING (
    SELECT p.id                                      AS id_pedido,
           dpe.sk_pessoa,
           to_char(p.dt_venda, 'YYYYMMDD')::integer  AS sk_tempo_criado,
           p.status                                  AS status_atual,
           p.dt_venda                                AS dt_criado,
           s.dt_pago, s.dt_separado, s.dt_enviado, s.dt_entregue,
           s.dt_cancelado, s.dt_devolvido,
           -- os tempos entre marcos, calculados UMA vez, aqui:
           round((extract(epoch FROM s.dt_pago     - p.dt_venda) / 3600)::numeric, 2) AS horas_ate_pagamento,
           round((extract(epoch FROM s.dt_enviado  - p.dt_venda) / 3600)::numeric, 2) AS horas_ate_envio,
           round((extract(epoch FROM s.dt_entregue - p.dt_venda) / 3600)::numeric, 2) AS horas_ate_entrega,
           p.valor_total,
           a.is_fraude
    FROM stg.pedidos p
    JOIN (  -- o PIVOT: cada status vira uma coluna de data
            SELECT id_pedido,
                   max(dt_evento) FILTER (WHERE status = 'pago')      AS dt_pago,
                   max(dt_evento) FILTER (WHERE status = 'separado')  AS dt_separado,
                   max(dt_evento) FILTER (WHERE status = 'enviado')   AS dt_enviado,
                   max(dt_evento) FILTER (WHERE status = 'entregue')  AS dt_entregue,
                   max(dt_evento) FILTER (WHERE status = 'cancelado') AS dt_cancelado,
                   max(dt_evento) FILTER (WHERE status = 'devolvido') AS dt_devolvido
            FROM stg.status_pedidos
            GROUP BY id_pedido
         ) s ON s.id_pedido = p.id
    JOIN stg.auditoria_pedidos a ON a.id_pedido = p.id
    JOIN dim_pessoas dpe ON dpe.id = p.id_pessoa
                        AND p.dt_venda >= dpe.dt_inicio
                        AND p.dt_venda <  COALESCE(dpe.dt_fim, 'infinity')
) AS o
ON f.id_pedido = o.id_pedido
-- o pedido avancou no ciclo desde a ultima carga: completa a linha
WHEN MATCHED AND (f.status_atual, f.dt_pago, f.dt_separado, f.dt_enviado, f.dt_entregue,
                  f.dt_cancelado, f.dt_devolvido, f.is_fraude)
                 IS DISTINCT FROM
                 (o.status_atual, o.dt_pago, o.dt_separado, o.dt_enviado, o.dt_entregue,
                  o.dt_cancelado, o.dt_devolvido, o.is_fraude) THEN
    UPDATE SET status_atual        = o.status_atual,
               dt_pago             = o.dt_pago,
               dt_separado         = o.dt_separado,
               dt_enviado          = o.dt_enviado,
               dt_entregue         = o.dt_entregue,
               dt_cancelado        = o.dt_cancelado,
               dt_devolvido        = o.dt_devolvido,
               horas_ate_pagamento = o.horas_ate_pagamento,
               horas_ate_envio     = o.horas_ate_envio,
               horas_ate_entrega   = o.horas_ate_entrega,
               is_fraude           = o.is_fraude
WHEN NOT MATCHED THEN
    INSERT (id_pedido, sk_pessoa, sk_tempo_criado, status_atual, dt_criado, dt_pago, dt_separado,
            dt_enviado, dt_entregue, dt_cancelado, dt_devolvido, horas_ate_pagamento,
            horas_ate_envio, horas_ate_entrega, valor_total, is_fraude)
    VALUES (o.id_pedido, o.sk_pessoa, o.sk_tempo_criado, o.status_atual, o.dt_criado, o.dt_pago,
            o.dt_separado, o.dt_enviado, o.dt_entregue, o.dt_cancelado, o.dt_devolvido,
            o.horas_ate_pagamento, o.horas_ate_envio, o.horas_ate_entrega, o.valor_total, o.is_fraude);

\echo ''
\echo '--- prova 1: o funil - quantos pedidos ja passaram por cada marco'
SELECT count(*)            AS criados,
       count(dt_pago)      AS pagos,
       count(dt_separado)  AS separados,
       count(dt_enviado)   AS enviados,
       count(dt_entregue)  AS entregues,
       count(dt_cancelado) AS cancelados,
       count(dt_devolvido) AS devolvidos
FROM fato_ciclo_pedido;

\echo '--- prova 2: a pergunta da Demanda 3 - quanto tempo leva cada etapa (em horas)'
SELECT round(avg(horas_ate_pagamento), 1) AS media_ate_pagamento,
       round(avg(horas_ate_envio), 1)     AS media_ate_envio,
       round(avg(horas_ate_entrega), 1)   AS media_ate_entrega
FROM fato_ciclo_pedido
WHERE status_atual = 'entregue';
