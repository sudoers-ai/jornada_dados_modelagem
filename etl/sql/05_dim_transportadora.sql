-- ==========================================================================
-- ETL - passo 05 - dim_transportadora (SCD tipo 1)
--
-- Uma dimensao pequena e estavel: quase uma copia da tabela de origem.
-- Mesmo assim ela ganha uma CHAVE SUBSTITUTA (`sk_transportadora`).
--
-- Por que nao usar o `id` do transacional como chave?
--   - o DW pode receber dados de mais de um sistema, com ids que colidem;
--   - o id de origem pode ser reaproveitado ou mudar;
--   - com SCD tipo 2 (passo 08) a mesma entidade tem VARIAS linhas, e o id
--     de origem deixa de ser unico.
-- A regra e uma so: no DW, quem liga fato e dimensao e sempre a `sk_`.
-- ==========================================================================
MERGE INTO dim_transportadora AS d
USING stg.transportadoras AS o
ON d.id = o.id
WHEN MATCHED AND (d.nome, d.cnpj, d.custo_por_kg)
                 IS DISTINCT FROM (o.nome, o.cnpj, o.custo_por_kg) THEN
    UPDATE SET nome = o.nome, cnpj = o.cnpj, custo_por_kg = o.custo_por_kg
WHEN NOT MATCHED THEN
    INSERT (id, nome, cnpj, custo_por_kg)
    VALUES (o.id, o.nome, o.cnpj, o.custo_por_kg);

\echo ''
\echo '--- prova: sk_ (chave do DW) ao lado do id (chave do transacional)'
SELECT sk_transportadora, id, nome, custo_por_kg FROM dim_transportadora ORDER BY sk_transportadora;
