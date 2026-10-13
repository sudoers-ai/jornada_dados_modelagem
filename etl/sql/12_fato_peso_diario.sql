-- ==========================================================================
-- ETL - passo 12 - fato_peso_diario: SNAPSHOT PERIODICO
--
-- GRAO: uma linha por DIA e TRANSPORTADORA.
--
-- E a resposta direta da Demanda 2: "queremos o historico diario do peso
-- transportado para negociar o frete". Em vez de recalcular isso sobre
-- milhares de entregas toda vez que alguem abre o dashboard, o resultado
-- fica PRONTO, um numero por dia.
--
-- Duas licoes aqui:
--
--  1. Esta fato nasce de OUTRA FATO (fato_entregas), nao do transacional.
--     E um agregado: menos linhas, mesma verdade, resposta instantanea.
--
--  2. NUNCA guarde MEDIA numa fato. Media nao se soma: a media de duas
--     medias nao e a media do todo. Guarde os INGREDIENTES (peso total e
--     quantidade) e deixe a divisao para a hora da consulta.
--
-- Como e pequena e derivada, a carga e simples: apaga e refaz.
-- ==========================================================================
BEGIN;

TRUNCATE fato_peso_diario;

INSERT INTO fato_peso_diario (sk_tempo, sk_transportadora, qtd_transportes, qtd_pedidos,
                              peso_total_gramas, valor_frete_total)
SELECT sk_tempo_saida,
       sk_transportadora,
       count(DISTINCT id_transporte),
       count(*),
       sum(peso_gramas),
       sum(valor_frete)
FROM fato_entregas
GROUP BY sk_tempo_saida, sk_transportadora;

COMMIT;

\echo ''
\echo '--- prova 1: o agregado fecha com a fato de origem'
SELECT (SELECT sum(peso_total_gramas) FROM fato_peso_diario) AS peso_no_agregado,
       (SELECT sum(peso_gramas) FROM fato_entregas)          AS peso_na_fato_entregas,
       (SELECT count(*) FROM fato_peso_diario)               AS linhas_no_agregado,
       (SELECT count(*) FROM fato_entregas)                  AS linhas_na_fato_entregas;

\echo '--- prova 2: a pergunta da Demanda 2 - peso medio por pedido, por mes'
SELECT t.ano, t.mes, t.nome_mes,
       sum(d.qtd_pedidos)                                             AS pedidos,
       round(sum(d.peso_total_gramas) / 1000.0)                       AS peso_total_kg,
       round(sum(d.peso_total_gramas) / 1000.0 / sum(d.qtd_pedidos), 2) AS peso_medio_kg_por_pedido,
       round(sum(d.valor_frete_total) / (sum(d.peso_total_gramas) / 1000.0), 2) AS custo_real_por_kg
FROM fato_peso_diario d
JOIN dim_tempo t ON t.sk_tempo = d.sk_tempo
GROUP BY t.ano, t.mes, t.nome_mes
ORDER BY t.ano, t.mes;
