SELECT d.device_id,
       d.modelo,
       d.fabricante,
       d.qtd_contas,
       COUNT(DISTINCT f.id_pedido) AS pedidos,
       SUM(f.valor_total)          AS valor_sob_suspeita
FROM dim_dispositivo d
INNER JOIN fato_pedidos f ON f.sk_dispositivo = d.sk_dispositivo
WHERE d.is_compartilhado
GROUP BY d.device_id, d.modelo, d.fabricante, d.qtd_contas
ORDER BY valor_sob_suspeita DESC
