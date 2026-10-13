-- ==========================================================================
-- Ajustes sobre o backup do Metabase herdado do repo liga_sudoers.
--
-- O arquivo 01_metabase_backup.sql e a copia FIEL do backup original
-- (liga_sudoers/dashboard/metabase_db/metabase_backup.sql). Ele traz o
-- usuario, as duas conexoes e os dois dashboards antigos.
--
-- Aqui ficam SO as diferencas necessarias para este repositorio:
--   1. as conexoes apontam para os containers daqui;
--   2. o Metabase enxerga apenas o schema `public` (o ETL novo cria os
--      schemas `oltp` e `stg` no DW, e eles nao sao para dashboard);
--   3. o conteudo de exemplo do proprio Metabase (Sample Database) sai,
--      para o aluno ver so o que e da Liga Sudoers.
-- ==========================================================================

-- 1 e 2) conexoes
UPDATE public.metabase_database
   SET details = (details::jsonb || '{"host": "postgres_oltp", "port": 5432, "schema-filters-type": "inclusion", "schema-filters-patterns": "public"}'::jsonb)::text
 WHERE name = 'Liga Sudoers';

UPDATE public.metabase_database
   SET details = (details::jsonb || '{"host": "postgres_dw", "port": 5432, "schema-filters-type": "inclusion", "schema-filters-patterns": "public"}'::jsonb)::text
 WHERE name = 'Liga DW';

-- 3) conteudo de exemplo
DELETE FROM public.report_dashboard  WHERE name = 'E-commerce Insights';
DELETE FROM public.metabase_database WHERE is_sample;
DELETE FROM public.setting           WHERE key = 'example-dashboard-id';
UPDATE public.collection SET archived = true WHERE name = 'Examples';

-- 4) a pagina inicial abre limpa, sem a propaganda de "incorporar o Metabase"
UPDATE public.setting SET value = 'hidden' WHERE key = 'embedding-homepage';
