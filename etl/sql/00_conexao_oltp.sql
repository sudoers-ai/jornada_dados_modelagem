-- ==========================================================================
-- ETL - passo 00 - A PONTE ENTRE OS DOIS BANCOS
--
-- O DW e o transacional sao dois servidores PostgreSQL diferentes. Para o DW
-- conseguir LER o transacional, usamos o postgres_fdw (foreign data wrapper):
-- ele faz as tabelas de la aparecerem aqui dentro, no schema `oltp`, como se
-- fossem locais. Nenhum dado e copiado neste passo - so a "janela" e aberta.
--
-- Isto e o "E" do ETL (Extract) sendo preparado.
-- ==========================================================================
SET client_min_messages = warning;

CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- Recria a ponte do zero a cada execucao: assim, se o transacional ganhou
-- tabelas ou colunas novas, o DW passa a enxerga-las.
DROP SERVER IF EXISTS servidor_oltp CASCADE;

CREATE SERVER servidor_oltp
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (host 'postgres_oltp', port '5432', dbname 'liga_sudoers');

CREATE USER MAPPING FOR CURRENT_USER
    SERVER servidor_oltp
    OPTIONS (user 'sudoers', password 'password');

DROP SCHEMA IF EXISTS oltp CASCADE;
CREATE SCHEMA oltp;

IMPORT FOREIGN SCHEMA public FROM SERVER servidor_oltp INTO oltp;

\echo ''
\echo '--- prova: o DW esta lendo o transacional AO VIVO (nada foi copiado ainda)'
SELECT (SELECT count(*) FROM oltp.pessoas)  AS pessoas_no_oltp,
       (SELECT count(*) FROM oltp.pedidos)  AS pedidos_no_oltp,
       (SELECT max(dt_venda) FROM oltp.pedidos) AS venda_mais_recente;
