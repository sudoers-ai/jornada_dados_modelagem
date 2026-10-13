-- ==========================================================================
-- ETL - passo 07 - dim_dispositivo: atributos DERIVADOS
--
-- Esta dimensao mostra o que "transformar" quer dizer de verdade. Tres
-- colunas dela NAO EXISTEM em lugar nenhum do transacional:
--
--   fabricante        -> extraido do texto do modelo ("iPhone 15" -> Apple)
--   qtd_contas        -> quantas pessoas DIFERENTES ja compraram por este
--                        aparelho (calculado cruzando auditoria e pedidos)
--   is_compartilhado  -> 3 contas ou mais no mesmo aparelho fisico
--
-- `is_compartilhado` e a resposta da Demanda 1: e assim que um ANEL DE
-- FRAUDE (varias contas, um aparelho so) deixa de ser invisivel. No
-- transacional, achar isso exige cruzar tres tabelas. Aqui e um filtro.
-- ==========================================================================
MERGE INTO dim_dispositivo AS d
USING (
    SELECT x.device_id,
           x.modelo,
           x.sistema,
           CASE
               WHEN x.modelo ILIKE 'iphone%'   OR x.modelo ILIKE 'ipad%' THEN 'Apple'
               WHEN x.modelo ILIKE 'samsung%'  THEN 'Samsung'
               WHEN x.modelo ILIKE 'motorola%' THEN 'Motorola'
               WHEN x.modelo ILIKE 'xiaomi%'   THEN 'Xiaomi'
               WHEN x.modelo ILIKE 'pixel%'    THEN 'Google'
               WHEN x.modelo ILIKE 'web%'      THEN 'Navegador'
               ELSE 'Outros'
           END                        AS fabricante,
           COALESCE(u.qtd_contas, 0)  AS qtd_contas
    FROM stg.dispositivos x
    LEFT JOIN (
        -- quantas pessoas diferentes usaram cada aparelho
        SELECT a.device_id, count(DISTINCT p.id_pessoa)::integer AS qtd_contas
        FROM stg.auditoria_pedidos a
        JOIN stg.pedidos p ON p.id = a.id_pedido
        GROUP BY a.device_id
    ) u ON u.device_id = x.device_id
) AS o
ON d.device_id = o.device_id
WHEN MATCHED AND (d.modelo, d.sistema, d.fabricante, d.qtd_contas)
                 IS DISTINCT FROM (o.modelo, o.sistema, o.fabricante, o.qtd_contas) THEN
    UPDATE SET modelo           = o.modelo,
               sistema          = o.sistema,
               fabricante       = o.fabricante,
               qtd_contas       = o.qtd_contas,
               is_compartilhado = o.qtd_contas >= 3
WHEN NOT MATCHED THEN
    INSERT (device_id, modelo, sistema, fabricante, qtd_contas, is_compartilhado)
    VALUES (o.device_id, o.modelo, o.sistema, o.fabricante, o.qtd_contas, o.qtd_contas >= 3);

\echo ''
\echo '--- prova: os aneis de fraude aparecem com um filtro'
SELECT device_id, modelo, fabricante, qtd_contas
FROM dim_dispositivo WHERE is_compartilhado ORDER BY qtd_contas DESC, device_id;
