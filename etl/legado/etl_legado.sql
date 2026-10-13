-- ==========================================================================
-- ETL LEGADO - o processo que a Liga Sudoers roda ha anos
--
-- E a mesma logica do repo liga_sudoers (datawarehouse_simulator), so que
-- lendo o transacional pela ponte do postgres_fdw (schema `oltp`).
--
-- Rode com:  make etl-legado
--
-- Leia com atencao: ele funciona, mas carrega TRES problemas que voce vai
-- corrigir nas proximas etapas. Eles estao marcados com (!).
-- ==========================================================================

-- 1) Staging: copia o que interessa do transacional -------------------------
\echo ''
\echo '1) staging: copiando do transacional'
TRUNCATE stg_pessoas, stg_produtos, stg_pedidos;

INSERT INTO stg_pessoas (id, nome, sexo, dt_nasc, created_at, updated_at)
SELECT id, nome, sexo, dt_nasc, created_at, updated_at
FROM oltp.pessoas;

INSERT INTO stg_produtos (id, cat_desc, descricao, created_at, updated_at)
SELECT p.id, c.descricao, p.descricao, p.created_at, p.updated_at
FROM oltp.produtos p
JOIN oltp.categorias c ON c.id = p.id_categoria;

INSERT INTO stg_pedidos (id_pedido, id_pessoa, id_produto, dispositivo, geohash, telefone,
                         dt_venda, qtde, valor_unit, valor_total)
SELECT p.id, p.id_pessoa, i.id_produto, a.dispositivo, a.geohash, a.telefone,
       p.dt_venda, i.qtde,
       i.valor_total AS valor_unit,   -- (!) 1: chama de "unitario" o que e o total do item
       p.valor_total                  -- (!) 2: o total do PEDIDO, repetido em cada ITEM
FROM oltp.pedidos p
JOIN oltp.itens_pedidos     i ON i.id_pedido = p.id
JOIN oltp.auditoria_pedidos a ON a.id_pedido = p.id;

-- 2) Dimensoes: insere o que ainda nao existe -------------------------------
\echo '2) dimensoes: dim_pessoas e dim_produtos'
INSERT INTO dim_pessoas (id, nome, sexo, dt_nasc, created_at, updated_at)
SELECT id, nome, sexo, dt_nasc, created_at, updated_at
FROM stg_pessoas s
WHERE NOT EXISTS (
    SELECT 1 FROM dim_pessoas d
    WHERE d.id = s.id AND d.nome = s.nome AND d.sexo = s.sexo AND d.dt_nasc = s.dt_nasc
      AND d.created_at = s.created_at AND d.updated_at = s.updated_at
);

INSERT INTO dim_produtos (id, cat_desc, descricao, created_at, updated_at)
SELECT id, cat_desc, descricao, created_at, updated_at
FROM stg_produtos s
WHERE NOT EXISTS (
    SELECT 1 FROM dim_produtos d
    WHERE d.id = s.id AND d.cat_desc = s.cat_desc AND d.descricao = s.descricao
      AND d.created_at = s.created_at AND d.updated_at = s.updated_at
);
-- (!) 3: se um produto ou pessoa MUDA, nasce uma 2a linha na dimensao, sem
--        data de validade. O JOIN da fato (logo abaixo) passa a casar com as
--        duas - e cada venda daquele produto e contada em dobro.

-- 3) Fato: troca os ids pelas chaves substitutas ----------------------------
\echo '3) fato: fato_pedidos'
INSERT INTO fato_pedidos (id_pedido, sk_pessoa, sk_produto, dispositivo, geohash, telefone,
                          dt_venda, qtde, valor_unit, total)
SELECT s.id_pedido, dp.sk_pessoa, pr.sk_produto, s.dispositivo, s.geohash, s.telefone,
       s.dt_venda, s.qtde, s.valor_unit, s.valor_total
FROM stg_pedidos s
JOIN dim_pessoas  dp ON dp.id = s.id_pessoa
JOIN dim_produtos pr ON pr.id = s.id_produto
WHERE NOT EXISTS (
    SELECT 1 FROM fato_pedidos f
    WHERE f.id_pedido = s.id_pedido AND f.sk_pessoa = dp.sk_pessoa
      AND f.sk_produto = pr.sk_produto AND f.dt_venda = s.dt_venda AND f.total = s.valor_total
);

\echo ''
\echo '--- o DW legado depois da carga'
SELECT (SELECT count(*) FROM dim_pessoas)  AS dim_pessoas,
       (SELECT count(*) FROM dim_produtos) AS dim_produtos,
       (SELECT count(*) FROM fato_pedidos) AS fato_pedidos;
