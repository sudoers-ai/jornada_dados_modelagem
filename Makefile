# ==========================================================================
# Liga Sudoers - Modelagem de Dados - atalhos
#
#   make ajuda      lista tudo
#
# Nada aqui e obrigatorio: todo `make` corresponde a um comando `docker`
# que esta escrito em docs/comandos.md. O Makefile so poupa digitacao.
# ==========================================================================
.DEFAULT_GOAL := ajuda
SHELL := /bin/bash
DC    := docker compose
FERR  := $(DC) --progress quiet run --rm ferramentas
PSQL_OLTP := psql -v ON_ERROR_STOP=1 -U sudoers -d liga_sudoers
PSQL_DW   := psql -v ON_ERROR_STOP=1 -U sudoers -d liga_sudoers_dw
# silencia os NOTICE ("ja existe, pulando") nos comandos de manutencao
QUIETO    := -e PGOPTIONS=--client-min-messages=warning

# Cria o .env na primeira vez (so para voce poder trocar uma porta ocupada).
$(shell [ -f .env ] || cp .env.example .env 2>/dev/null)

.PHONY: ajuda verificar subir status derruba limpar logs consertar diagnostico \
        psql-oltp psql-dw sql-oltp sql-dw conferir-oltp conferir-dw \
        historico streaming streaming-fundo streaming-parar streaming-logs \
        etl-legado etl etl-passo validar metabase-sync conferir-dashboards \
        gabarito-oltp gabarito-dw gabarito-dashboards reset-oltp reset-dw

ajuda:  ## mostra esta ajuda
	@echo ""
	@echo "  Liga Sudoers - Modelagem de Dados"
	@echo "  ---------------------------------------------------------------"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ---------------------------------------------------------------- ambiente
verificar:   ## confere Docker, portas e memoria ANTES de subir
	@bash scripts/verificar.sh

subir:       ## sobe os bancos e o Metabase e espera ficarem prontos
	$(DC) up -d --build
	@$(DC) build -q ferramentas
	@echo "aguardando os containers ficarem prontos (o Metabase leva 1 a 2 minutos)..."
	@bash scripts/esperar.sh tudo
	@echo ""
	@echo "  Tudo no ar. Continue em modelagem/01_legado/README.md"
	@echo ""

status:      ## mostra o estado dos containers
	@$(DC) ps -a --format 'table {{.Name}}\t{{.Service}}\t{{.Status}}'

derruba:     ## para os containers (MANTEM os dados)
	$(DC) --profile streaming --profile ferramentas down

limpar:      ## para tudo e APAGA os dados (recomeca do zero)
	$(DC) --profile streaming --profile ferramentas down -v

logs:        ## segue os logs de um servico (make logs s=metabase)
	$(DC) logs -f $(s)

consertar:   ## recria os containers (NAO apaga os dados)
	$(DC) up -d --force-recreate
	@bash scripts/esperar.sh tudo

diagnostico: ## junta tudo que o instrutor precisa para te ajudar
	@bash scripts/diagnostico.sh

# ------------------------------------------------------------------ bancos
psql-oltp:   ## abre o psql no banco TRANSACIONAL (saia com \q)
	@docker exec -it modelagem_oltp $(PSQL_OLTP)

psql-dw:     ## abre o psql no banco DIMENSIONAL (saia com \q)
	@docker exec -it modelagem_dw $(PSQL_DW)

sql-oltp:    ## roda um arquivo .sql no TRANSACIONAL (make sql-oltp f=caminho.sql)
	@test -n "$(f)" || (echo "uso: make sql-oltp f=caminho/do/arquivo.sql" && exit 1)
	@docker exec -i modelagem_oltp $(PSQL_OLTP) -f /repo/$(f)

sql-dw:      ## roda um arquivo .sql no DIMENSIONAL (make sql-dw f=caminho.sql)
	@test -n "$(f)" || (echo "uso: make sql-dw f=caminho/do/arquivo.sql" && exit 1)
	@docker exec -i modelagem_dw $(PSQL_DW) -f /repo/$(f)

# ------------------------------------------------- conferencia da modelagem
conferir-oltp: ## compara o SEU transacional com o modelo (DBML)
	@bash scripts/esperar.sh
	@$(FERR) python data_simulator/verificador.py oltp

conferir-dw:   ## compara o SEU dimensional com o modelo (DBML)
	@bash scripts/esperar.sh
	@$(FERR) python data_simulator/verificador.py dw

# ---------------------------------------------------------- geracao de dados
historico:   ## gera o historico de pedidos (so roda se o OLTP estiver certo)
	@bash scripts/esperar.sh
	@$(FERR) python data_simulator/liga_sudoers_historico.py $(n) $(args)

streaming:   ## gera dados continuamente (Ctrl+C para parar; ciclos=N para limitar)
	@bash scripts/esperar.sh
	@$(FERR) python data_simulator/liga_sudoers_streaming.py $(if $(ciclos),--ciclos $(ciclos)) $(if $(intervalo),--intervalo $(intervalo)) $(args)

streaming-fundo:  ## liga o streaming em segundo plano
	@bash scripts/esperar.sh
	@$(DC) --progress quiet --profile streaming up -d streaming
	@echo "streaming ligado em segundo plano. Acompanhe: make streaming-logs | Pare: make streaming-parar"

streaming-logs:   ## acompanha o streaming em segundo plano
	@$(DC) --profile streaming logs -f --tail 30 streaming

streaming-parar:  ## desliga o streaming em segundo plano
	@$(DC) --profile streaming rm -sf streaming >/dev/null 2>&1 || true
	@echo "streaming desligado."

# --------------------------------------------------------------------- ETL
etl-legado:  ## roda o ETL ANTIGO (carrega o DW legado)
	@bash scripts/esperar.sh
	@docker exec -i modelagem_dw $(PSQL_DW) -q -f /repo/etl/sql/00_conexao_oltp.sql
	@docker exec -i modelagem_dw $(PSQL_DW) -f /repo/etl/legado/etl_legado.sql

etl: conferir-dw  ## roda o ETL NOVO inteiro (so roda se o DW estiver certo)
	@for f in etl/sql/*.sql; do \
	  echo ""; echo "▶ $$f"; \
	  docker exec -i modelagem_dw $(PSQL_DW) -f /repo/$$f || { echo ""; echo "❌ o ETL parou em $$f"; exit 1; }; \
	done
	@echo ""
	@echo "✅ ETL concluido."

etl-passo:   ## roda UM passo do ETL novo (make etl-passo p=08)
	@test -n "$(p)" || (echo "uso: make etl-passo p=08" && exit 1)
	@f=$$(ls etl/sql/$(p)_*.sql 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "nao achei etl/sql/$(p)_*.sql"; exit 1; }; \
	 echo "▶ $$f"; docker exec -i modelagem_dw $(PSQL_DW) -f /repo/$$f

# ----------------------------------------------------------------- validacao
validar:     ## confere se OLTP e DW estao coerentes (o seu guia de evidencias)
	@bash scripts/esperar.sh
	@$(FERR) python tests/validar.py $(args)

metabase-sync: ## pede ao Metabase para reler as tabelas dos dois bancos
	@$(FERR) python dashboard/metabase.py sync

conferir-dashboards: ## roda todos os graficos e diz o que falta nos dashboards
	@$(FERR) python dashboard/metabase.py conferir

# ----------------------------------------------------------------- gabaritos
gabarito-oltp: ## aplica a RESPOSTA da evolucao do transacional
	@docker exec -i $(QUIETO) modelagem_oltp $(PSQL_OLTP) -q -f /repo/modelagem/ddl/gabarito/oltp_evolucao.sql
	@$(FERR) python data_simulator/verificador.py oltp || { \
	  echo "   O gabarito so ACRESCENTA o que falta: ele nao desfaz uma coluna criada com"; \
	  echo "   tipo ou obrigatoriedade diferente do modelo. Corrija as linhas acima, ou"; \
	  echo "   recomece o transacional do zero (APAGA os pedidos):"; \
	  echo "       make reset-oltp && make gabarito-oltp && make historico"; \
	  echo ""; exit 1; }

gabarito-dw:   ## aplica a RESPOSTA da evolucao do dimensional
	@docker exec -i $(QUIETO) modelagem_dw $(PSQL_DW) -q -f /repo/modelagem/ddl/gabarito/dw_evolucao.sql
	@$(FERR) python data_simulator/verificador.py dw || { \
	  echo "   O gabarito so ACRESCENTA o que falta: ele nao desfaz uma coluna criada com"; \
	  echo "   tipo ou obrigatoriedade diferente do modelo. Corrija as linhas acima, ou"; \
	  echo "   recomece o dimensional do zero (ele e reconstruido pelo ETL):"; \
	  echo "       make reset-dw && make gabarito-dw && make etl"; \
	  echo ""; exit 1; }

gabarito-dashboards: ## aplica a RESPOSTA dos dashboards no Metabase
	@$(FERR) python dashboard/metabase.py gabarito

reset-oltp:  ## volta o TRANSACIONAL ao legado (APAGA os dados dele)
	@echo "Voltando o transacional para a modelagem legada..."
	@$(MAKE) --no-print-directory streaming-parar
	@docker exec -i $(QUIETO) modelagem_oltp $(PSQL_OLTP) -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@docker exec -i $(QUIETO) modelagem_oltp $(PSQL_OLTP) -q -f /repo/modelagem/ddl/legado/01_oltp_schema.sql
	@docker exec -i $(QUIETO) modelagem_oltp $(PSQL_OLTP) -q -f /repo/modelagem/ddl/legado/02_oltp_dados_base.sql >/dev/null
	@echo "✅ transacional de volta ao legado (6 tabelas, sem pedidos)."

reset-dw:    ## volta o DIMENSIONAL ao legado (APAGA os dados dele)
	@echo "Voltando o dimensional para a modelagem legada..."
	@docker exec -i $(QUIETO) modelagem_dw $(PSQL_DW) -q -c "DROP SCHEMA IF EXISTS stg CASCADE; DROP SCHEMA IF EXISTS oltp CASCADE; DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@docker exec -i $(QUIETO) modelagem_dw $(PSQL_DW) -q -f /repo/modelagem/ddl/legado/03_dw_schema.sql
	@echo "✅ dimensional de volta ao legado (vazio)."
