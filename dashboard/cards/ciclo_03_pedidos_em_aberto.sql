SELECT status_atual AS situacao,
       COUNT(*)     AS pedidos
FROM fato_ciclo_pedido
WHERE status_atual NOT IN ('entregue', 'cancelado', 'devolvido')
GROUP BY status_atual
ORDER BY pedidos DESC
