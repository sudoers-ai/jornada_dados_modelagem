-- ==========================================================================
-- ETL - passo 03 - dim_localidade: a regra de negocio vira dado
--
-- No transacional a UF e um texto de 2 letras solto na auditoria. Quem
-- sabia que "a Liga Sudoers so atende SP, MG e RJ" era o analista, que
-- escrevia isso num CASE dentro do dashboard (voce viu no card antigo).
--
-- No dimensional, a regra vira uma COLUNA: `is_area_atendida`. Agora todo
-- relatorio usa a mesma regra, e mudar a regra e mudar um dado.
--
-- Esta dimensao tambem nao vem de tabela nenhuma do transacional: a lista
-- de UFs e conhecimento do negocio, carregada uma vez.
-- ==========================================================================
INSERT INTO dim_localidade (uf, nome_uf, regiao, is_area_atendida)
SELECT uf, nome_uf, regiao, uf IN ('SP', 'MG', 'RJ')
FROM (VALUES
    ('AC', 'Acre',                'Norte'),
    ('AL', 'Alagoas',             'Nordeste'),
    ('AP', 'Amapá',               'Norte'),
    ('AM', 'Amazonas',            'Norte'),
    ('BA', 'Bahia',               'Nordeste'),
    ('CE', 'Ceará',               'Nordeste'),
    ('DF', 'Distrito Federal',    'Centro-Oeste'),
    ('ES', 'Espírito Santo',      'Sudeste'),
    ('GO', 'Goiás',               'Centro-Oeste'),
    ('MA', 'Maranhão',            'Nordeste'),
    ('MT', 'Mato Grosso',         'Centro-Oeste'),
    ('MS', 'Mato Grosso do Sul',  'Centro-Oeste'),
    ('MG', 'Minas Gerais',        'Sudeste'),
    ('PA', 'Pará',                'Norte'),
    ('PB', 'Paraíba',             'Nordeste'),
    ('PR', 'Paraná',              'Sul'),
    ('PE', 'Pernambuco',          'Nordeste'),
    ('PI', 'Piauí',               'Nordeste'),
    ('RJ', 'Rio de Janeiro',      'Sudeste'),
    ('RN', 'Rio Grande do Norte', 'Nordeste'),
    ('RS', 'Rio Grande do Sul',   'Sul'),
    ('RO', 'Rondônia',            'Norte'),
    ('RR', 'Roraima',             'Norte'),
    ('SC', 'Santa Catarina',      'Sul'),
    ('SP', 'São Paulo',           'Sudeste'),
    ('SE', 'Sergipe',             'Nordeste'),
    ('TO', 'Tocantins',           'Norte')
) AS t (uf, nome_uf, regiao)
ON CONFLICT (uf) DO NOTHING;

\echo ''
\echo '--- prova: 27 UFs, 3 atendidas'
SELECT regiao, count(*) AS ufs, count(*) FILTER (WHERE is_area_atendida) AS atendidas
FROM dim_localidade GROUP BY regiao ORDER BY regiao;
