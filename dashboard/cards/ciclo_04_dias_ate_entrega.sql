SELECT DATE_TRUNC('week', dt_criado)::date    AS semana,
       ROUND(AVG(horas_ate_entrega) / 24, 2)  AS dias_ate_entrega
FROM fato_ciclo_pedido
WHERE dt_entregue IS NOT NULL
  AND dt_criado < CURRENT_DATE - 14           -- semanas ja "fechadas": as recentes ainda tem pedido na estrada
GROUP BY 1
ORDER BY 1
