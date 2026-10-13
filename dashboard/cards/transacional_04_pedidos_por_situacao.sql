SELECT status   AS situacao,
       count(*) AS pedidos
FROM pedidos
WHERE dt_venda >= now() - interval '7 days'
GROUP BY 1
ORDER BY 2 DESC
