-- ==========================================================================
-- ETL - passo 06 - dim_forma_pagamento: um ATRIBUTO vira ENTIDADE
--
-- No transacional, a forma de pagamento e so um texto na tabela pagamentos
-- ('pix', 'cartao_credito'...). Nao existe uma tabela "formas de pagamento".
--
-- No dimensional ela vira uma dimensao propria. Regra pratica:
--   tudo pelo que voce quer AGRUPAR ou FILTRAR e candidato a dimensao.
--
-- E ja aproveitamos para enriquecer: um nome apresentavel e um atributo
-- derivado (`is_a_vista`) que nao existe na origem.
-- ==========================================================================
INSERT INTO dim_forma_pagamento (forma, descricao, is_a_vista)
SELECT DISTINCT
       forma,
       CASE forma
           WHEN 'pix'            THEN 'Pix'
           WHEN 'cartao_credito' THEN 'Cartão de crédito'
           WHEN 'cartao_debito'  THEN 'Cartão de débito'
           WHEN 'boleto'         THEN 'Boleto bancário'
           ELSE initcap(replace(forma, '_', ' '))
       END,
       forma <> 'cartao_credito'
FROM stg.pagamentos
ON CONFLICT (forma) DO NOTHING;

\echo ''
\echo '--- prova: 4 formas de pagamento, com descricao e atributo derivado'
SELECT * FROM dim_forma_pagamento ORDER BY sk_forma_pagamento;
