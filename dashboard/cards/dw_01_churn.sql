SELECT atual.nome        AS cliente,
       atual.cidade,
       atual.uf,
       MAX(fp.dt_venda)  AS ultima_compra
FROM fato_pedidos fp
INNER JOIN dim_pessoas dp    ON dp.sk_pessoa = fp.sk_pessoa
INNER JOIN dim_pessoas atual ON atual.id = dp.id AND atual.is_atual   -- a versao ATUAL da mesma pessoa
GROUP BY atual.id, atual.nome, atual.cidade, atual.uf                 -- por id: homonimos nao se misturam
HAVING MAX(fp.dt_venda) < CURRENT_DATE - INTERVAL '7 days'
ORDER BY ultima_compra
