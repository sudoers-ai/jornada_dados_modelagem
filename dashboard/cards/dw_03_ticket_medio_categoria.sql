SELECT dp.cat_desc AS categoria,
       ROUND(SUM(fp.valor_total) / COUNT(DISTINCT fp.id_pedido), 2) AS ticket_medio
FROM fato_pedidos fp
INNER JOIN dim_produtos dp ON fp.sk_produto = dp.sk_produto           -- sk com sk (antes: sk com id!)
WHERE NOT fp.is_fraude
  AND fp.status NOT IN ('cancelado', 'devolvido')
GROUP BY dp.cat_desc
ORDER BY ticket_medio DESC
