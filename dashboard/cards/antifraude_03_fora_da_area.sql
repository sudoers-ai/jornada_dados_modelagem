SELECT l.nome_uf                   AS uf,
       COUNT(DISTINCT f.id_pedido) AS pedidos
FROM fato_pedidos f
INNER JOIN dim_localidade l ON l.sk_localidade = f.sk_localidade
WHERE NOT l.is_area_atendida
GROUP BY l.nome_uf
ORDER BY pedidos DESC
