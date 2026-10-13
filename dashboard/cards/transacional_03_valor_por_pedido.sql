SELECT id          AS pedido,
       valor_total AS sum                            -- uma linha por PEDIDO: a media disto e o ticket medio
FROM pedidos
WHERE dt_venda >= now() - interval '7 days'
  AND status NOT IN ('cancelado', 'devolvido')
ORDER BY 2 DESC
