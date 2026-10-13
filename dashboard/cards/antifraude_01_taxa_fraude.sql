SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE is_fraude) / COUNT(*), 2) AS taxa_fraude_pct
FROM fato_ciclo_pedido
