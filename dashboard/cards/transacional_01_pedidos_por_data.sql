SELECT cast(dt_venda AS date) AS dt_venda,
       count(*)               AS qtde_vendas,
       sum(valor_total)       AS total_vendas
FROM pedidos
WHERE dt_venda >= current_date - 6                   -- os ULTIMOS 7 dias
  AND status NOT IN ('cancelado', 'devolvido')       -- campo novo: venda cancelada nao e venda
GROUP BY 1
ORDER BY 1
