-- ==========================================================================
-- ETL - passo 02 - dim_tempo: a dimensao que NAO vem do transacional
--
-- No transacional, data e so uma coluna (`dt_venda`). No dimensional ela vira
-- uma TABELA: uma linha por dia, com tudo que se quer saber sobre aquele dia
-- ja calculado (mes, trimestre, dia da semana, fim de semana, feriado).
--
-- Por que? Porque "vendas em feriado" ou "vendas por trimestre" passam a ser
-- um filtro simples, igual em todo relatorio - e nao um EXTRACT() ou um CASE
-- que cada analista escreve de um jeito.
--
-- A chave e um inteiro legivel: 20261013 = 13/10/2026.
-- ==========================================================================
INSERT INTO dim_tempo (sk_tempo, data, ano, trimestre, mes, nome_mes, semana_ano,
                       dia, dia_semana, nome_dia, is_fim_semana, is_feriado)
SELECT
    to_char(d, 'YYYYMMDD')::integer                       AS sk_tempo,
    d::date                                               AS data,
    extract(year    FROM d)::integer                      AS ano,
    extract(quarter FROM d)::integer                      AS trimestre,
    extract(month   FROM d)::integer                      AS mes,
    (ARRAY['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
           'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    )[extract(month FROM d)::integer]                     AS nome_mes,
    extract(week    FROM d)::integer                      AS semana_ano,
    extract(day     FROM d)::integer                      AS dia,
    extract(isodow  FROM d)::integer                      AS dia_semana,
    (ARRAY['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
           'Sexta-feira', 'Sábado', 'Domingo']
    )[extract(isodow FROM d)::integer]                    AS nome_dia,
    extract(isodow FROM d) IN (6, 7)                      AS is_fim_semana,
    -- feriados nacionais de data fixa
    to_char(d, 'MM-DD') IN ('01-01', '04-21', '05-01', '09-07', '10-12',
                            '11-02', '11-15', '11-20', '12-25') AS is_feriado
FROM generate_series(
         -- do 1o dia do ano da venda mais antiga...
         (SELECT date_trunc('year', min(dt_venda)) FROM stg.pedidos),
         -- ...ate o ultimo dia do ano que vem (entregas previstas caem no futuro)
         date_trunc('year', now()) + interval '2 years' - interval '1 day',
         interval '1 day'
     ) AS d
ON CONFLICT (sk_tempo) DO NOTHING;      -- dia que ja existe nao e inserido de novo

\echo ''
\echo '--- prova: o calendario'
SELECT count(*) AS dias, min(data) AS primeiro_dia, max(data) AS ultimo_dia,
       count(*) FILTER (WHERE is_fim_semana) AS fins_de_semana,
       count(*) FILTER (WHERE is_feriado)    AS feriados
FROM dim_tempo;

SELECT sk_tempo, data, nome_dia, nome_mes, trimestre, is_fim_semana, is_feriado
FROM dim_tempo WHERE data = current_date;
