SELECT DATE_TRUNC('month', dt_venda) AS mes,
       SUM(valor_total)              AS faturamento_mensal            -- valor do ITEM: nao conta em dobro
FROM fato_pedidos
WHERE dt_venda >= CURRENT_DATE - INTERVAL '6 months'
  AND NOT is_fraude                                                   -- fraude nao e faturamento
  AND status NOT IN ('cancelado', 'devolvido')
GROUP BY DATE_TRUNC('month', dt_venda)
ORDER BY mes
