SELECT t.data,
       ROUND(SUM(d.peso_total_gramas) / 1000.0 / SUM(d.qtd_pedidos), 2) AS peso_medio_kg
FROM fato_peso_diario d
INNER JOIN dim_tempo t ON t.sk_tempo = d.sk_tempo
WHERE t.data >= CURRENT_DATE - 60
GROUP BY t.data
ORDER BY t.data
