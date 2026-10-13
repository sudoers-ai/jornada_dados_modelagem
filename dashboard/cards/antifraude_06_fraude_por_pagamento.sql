SELECT p.descricao AS forma_pagamento,
       ROUND(100.0 * COUNT(DISTINCT f.id_pedido) FILTER (WHERE f.is_fraude)
             / COUNT(DISTINCT f.id_pedido), 2) AS taxa_fraude_pct
FROM fato_pedidos f
INNER JOIN dim_forma_pagamento p ON p.sk_forma_pagamento = f.sk_forma_pagamento
GROUP BY p.descricao
ORDER BY taxa_fraude_pct DESC
