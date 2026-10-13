SELECT t.nome                                                           AS transportadora,
       t.custo_por_kg,
       COUNT(*)                                                         AS entregas,
       ROUND(100.0 * COUNT(*) FILTER (WHERE f.is_atrasada) / COUNT(*), 1) AS pct_atrasadas,
       ROUND(AVG(f.dias_transito), 1)                                   AS media_dias_transito,
       SUM(f.valor_frete)                                               AS frete_pago
FROM fato_entregas f
INNER JOIN dim_transportadora t ON t.sk_transportadora = f.sk_transportadora
GROUP BY t.nome, t.custo_por_kg
ORDER BY t.custo_por_kg
