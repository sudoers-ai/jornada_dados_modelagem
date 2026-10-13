SELECT COUNT(*) AS pedidos_em_transito
FROM fato_entregas
WHERE NOT is_entregue
