SELECT TO_CHAR(tp.data, 'YYYY-MM') AS mes,
       t.nome                      AS transportadora,
       SUM(d.valor_frete_total)    AS frete
FROM fato_peso_diario d
INNER JOIN dim_tempo tp         ON tp.sk_tempo = d.sk_tempo
INNER JOIN dim_transportadora t ON t.sk_transportadora = d.sk_transportadora
GROUP BY 1, 2
ORDER BY 1, 2
