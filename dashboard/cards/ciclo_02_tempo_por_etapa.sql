SELECT etapa, horas
FROM (
    SELECT 1 AS ordem, '1. Compra ate pagamento' AS etapa,
           ROUND(AVG(horas_ate_pagamento), 1) AS horas
    FROM fato_ciclo_pedido WHERE dt_entregue IS NOT NULL
    UNION ALL
    SELECT 2, '2. Pagamento ate envio',
           ROUND(AVG(horas_ate_envio - horas_ate_pagamento), 1)
    FROM fato_ciclo_pedido WHERE dt_entregue IS NOT NULL
    UNION ALL
    SELECT 3, '3. Envio ate entrega',
           ROUND(AVG(horas_ate_entrega - horas_ate_envio), 1)
    FROM fato_ciclo_pedido WHERE dt_entregue IS NOT NULL
) AS etapas
ORDER BY ordem
