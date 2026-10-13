SELECT etapa, pedidos
FROM (
    SELECT 1 AS ordem, 'Criado' AS etapa, COUNT(*) AS pedidos FROM fato_ciclo_pedido
    UNION ALL SELECT 2, 'Pago',     COUNT(dt_pago)     FROM fato_ciclo_pedido
    UNION ALL SELECT 3, 'Separado', COUNT(dt_separado) FROM fato_ciclo_pedido
    UNION ALL SELECT 4, 'Enviado',  COUNT(dt_enviado)  FROM fato_ciclo_pedido
    UNION ALL SELECT 5, 'Entregue', COUNT(dt_entregue) FROM fato_ciclo_pedido
) AS funil
ORDER BY ordem
