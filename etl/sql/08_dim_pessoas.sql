-- ==========================================================================
-- ETL - passo 08 - dim_pessoas: guardar o PASSADO (SCD tipo 2)
--
-- O problema: a Maria morava em Campinas e mudou para Santos. No
-- transacional, o endereco principal dela agora e Santos - e pronto.
-- Se o DW simplesmente sobrescrevesse (tipo 1), TODAS as compras antigas da
-- Maria passariam a contar como vendas "para Santos". O relatorio de vendas
-- por cidade do ano passado mudaria sozinho. Relatorio que muda o passado
-- nao serve para decisao.
--
-- A solucao (SCD tipo 2): a Maria passa a ter DUAS linhas na dimensao.
--
--   sk_pessoa | id | cidade   | dt_inicio  | dt_fim     | is_atual
--   ----------+----+----------+------------+------------+---------
--        17   | 17 | Campinas | 1900-01-01 | 2026-07-02 | false
--       512   | 17 | Santos   | 2026-07-02 |   (nulo)   | true
--
-- Cada venda aponta para a `sk_pessoa` que valia NO DIA da venda. As vendas
-- antigas continuam em Campinas para sempre.
--
-- Repare: o `id` (17) se repete. E por isso que o DW precisa de chave
-- substituta - a chave do transacional deixou de identificar UMA linha.
-- ==========================================================================

-- 1) Cada endereco que a pessoa ja teve vira uma VERSAO dela.
--    So entram os enderecos que ainda nao viraram versao (id_endereco novo).
INSERT INTO dim_pessoas (id, nome, sexo, dt_nasc, id_endereco, cidade, uf,
                         dt_inicio, dt_fim, is_atual, created_at, updated_at)
SELECT p.id, p.nome, p.sexo, p.dt_nasc,
       e.id, e.cidade, e.uf,
       e.created_at,              -- a versao comeca quando o endereco nasceu
       NULL, true,
       p.created_at, p.updated_at
FROM stg.pessoas p
JOIN stg.enderecos e ON e.id_pessoa = p.id
WHERE NOT EXISTS (SELECT 1 FROM dim_pessoas d WHERE d.id_endereco = e.id);

-- 2) Fecha as versoes antigas: cada versao vale ate a proxima comecar.
--    LEAD() olha "a linha seguinte" da mesma pessoa, em ordem de data.
WITH versoes AS (
    SELECT sk_pessoa,
           row_number() OVER w    AS ordem,
           lead(dt_inicio) OVER w AS inicio_da_proxima
    FROM dim_pessoas
    WINDOW w AS (PARTITION BY id ORDER BY dt_inicio, id_endereco)
)
UPDATE dim_pessoas d
SET dt_inicio = CASE WHEN v.ordem = 1 THEN timestamp '1900-01-01' ELSE d.dt_inicio END,
    dt_fim    = v.inicio_da_proxima,
    is_atual  = v.inicio_da_proxima IS NULL
FROM versoes v
WHERE v.sk_pessoa = d.sk_pessoa
  AND (d.dt_fim, d.is_atual, d.dt_inicio)
      IS DISTINCT FROM (v.inicio_da_proxima,
                        v.inicio_da_proxima IS NULL,
                        CASE WHEN v.ordem = 1 THEN timestamp '1900-01-01' ELSE d.dt_inicio END);
-- (a 1a versao comeca em 1900 para valer para qualquer venda antiga)

-- 3) O que NAO precisa de historico continua tipo 1: se o nome foi corrigido,
--    corrige em todas as versoes.
UPDATE dim_pessoas d
SET nome = p.nome, sexo = p.sexo, dt_nasc = p.dt_nasc, updated_at = p.updated_at
FROM stg.pessoas p
WHERE p.id = d.id
  AND (d.nome, d.sexo, d.dt_nasc) IS DISTINCT FROM (p.nome, p.sexo, p.dt_nasc);

\echo ''
\echo '--- prova 1: mais linhas na dimensao do que pessoas (quem se mudou tem 2 ou mais)'
SELECT count(*)                          AS linhas_na_dimensao,
       count(DISTINCT id)                AS pessoas,
       count(*) FILTER (WHERE is_atual)  AS versoes_atuais,
       count(*) FILTER (WHERE NOT is_atual) AS versoes_antigas
FROM dim_pessoas;

\echo '--- prova 2: a historia de uma pessoa que se mudou'
SELECT sk_pessoa, id, nome, cidade, uf, dt_inicio::date, dt_fim::date, is_atual
FROM dim_pessoas
WHERE id = (SELECT id FROM dim_pessoas GROUP BY id HAVING count(*) > 1 ORDER BY id LIMIT 1)
ORDER BY dt_inicio;
