SELECT nome_dia, pedidos
FROM (
    SELECT t.dia_semana, t.nome_dia, COUNT(*) AS pedidos
    FROM fato_ciclo_pedido f
    INNER JOIN dim_tempo t ON t.sk_tempo = f.sk_tempo_criado          -- dia da semana pronto, sem EXTRACT
    GROUP BY t.dia_semana, t.nome_dia
) AS dias
ORDER BY dia_semana
