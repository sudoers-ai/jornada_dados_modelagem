SELECT CASE WHEN dt_enviado IS NULL THEN 'Barrada antes do envio'
            ELSE 'Descoberta depois do envio'
       END              AS desfecho,
       SUM(valor_total) AS valor
FROM fato_ciclo_pedido
WHERE is_fraude
GROUP BY 1
ORDER BY 1
