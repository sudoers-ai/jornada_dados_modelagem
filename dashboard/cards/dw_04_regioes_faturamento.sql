SELECT l.uf,
       SUM(f.valor_total) AS faturamento
FROM fato_pedidos f
INNER JOIN dim_localidade l ON l.sk_localidade = f.sk_localidade      -- a UF vem da dimensao, sem CASE
WHERE NOT f.is_fraude
  AND f.status NOT IN ('cancelado', 'devolvido')
GROUP BY l.uf
ORDER BY faturamento DESC
