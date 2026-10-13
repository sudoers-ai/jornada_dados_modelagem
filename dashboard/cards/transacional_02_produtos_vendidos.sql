SELECT p.descricao,
       sum(ip.qtde)        AS count,                 -- unidades vendidas
       sum(ip.valor_total) AS sum                    -- valor vendido (quantidade x preco)
FROM pedidos ped
INNER JOIN itens_pedidos ip ON ip.id_pedido = ped.id
INNER JOIN produtos p ON p.id = ip.id_produto
WHERE ped.dt_venda >= now() - interval '7 days'
  AND ped.status NOT IN ('cancelado', 'devolvido')
GROUP BY 1
ORDER BY 3 DESC
