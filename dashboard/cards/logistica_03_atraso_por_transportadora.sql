SELECT t.nome AS transportadora,
       ROUND(100.0 * COUNT(*) FILTER (WHERE f.is_atrasada) / COUNT(*), 1) AS pct_atrasadas
FROM fato_entregas f
INNER JOIN dim_transportadora t ON t.sk_transportadora = f.sk_transportadora
GROUP BY t.nome
ORDER BY pct_atrasadas DESC
