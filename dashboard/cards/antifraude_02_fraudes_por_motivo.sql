SELECT motivo_fraude             AS motivo,
       COUNT(DISTINCT id_pedido) AS pedidos
FROM fato_pedidos
WHERE is_fraude
GROUP BY motivo_fraude
ORDER BY pedidos DESC
