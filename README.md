# 📐 Liga Sudoers — Modelagem de Dados

![Desafio Engenheiro de Dados](Desafio%20-%20Jornada%20Engenharia%20de%20Dados.png "Desafio Engenheiro de Dados")

> Parte 3 da **Jornada Engenharia de Dados**. Nas outras partes você move o
> dado ([`jornada_dados`](https://github.com/sudoers-ai/jornada_dados)) e
> escolhe onde ele mora ([`jornada_dados_nosql`](https://github.com/sudoers-ai/jornada_dados_nosql)).
> Aqui você dá **forma** a ele.
>
> Este repositório é **autocontido**: não depende de nenhum outro para ser
> concluído. Você só precisa de Docker.

Bem-vindo ao Mapa do Engenheiro de Dados, módulo **Data Modeling**. Este é um
laboratório 100% prático: você recebe uma empresa funcionando, com um banco
transacional, um Data Warehouse e dashboards — e três demandas da diretoria
que a modelagem atual **não consegue responder**.

O seu trabalho é evoluir a modelagem, dos dois lados, até responder.

---

## 🎯 O que você vai aprender

Não é "como escrever `CREATE TABLE`". É **por que a mesma informação precisa
de dois desenhos diferentes**.

| No banco transacional (OLTP) | No banco dimensional (DW) |
|---|---|
| O objetivo é **gravar** sem errar | O objetivo é **responder** sem pensar em `JOIN` |
| 3ª forma normal: cada fato num lugar só | Star schema: fatos no centro, dimensões em volta |
| Guarda como as coisas **estão** | Guarda como as coisas **eram** em cada momento |
| Muitas tabelas pequenas | Poucas tabelas largas |

Ao final você terá feito, com as próprias mãos:

* a evolução de um modelo transacional em produção (colunas novas, tabelas
  novas, chaves estrangeiras, relacionamento N:N, triggers);
* a conversão desse modelo para o dimensional — entendendo que **o dado não é
  copiado, é transformado**;
* os três tipos de tabela fato (transacional, snapshot periódico e snapshot
  acumulado) e os dois tipos mais usados de dimensão (SCD tipo 1 e tipo 2);
* um ETL em SQL puro, passo a passo;
* dashboards que respondem às três demandas.

---

## 📨 As três demandas

A Liga Sudoers é um e-commerce que só entrega em **SP, MG e RJ**. A diretoria
chegou com três pedidos:

| # | Quem pediu | O pedido |
|---|---|---|
| 1 | **Antifraude** | "Clientes reclamam de compras que não fizeram. Quero saber onde, por qual aparelho e por qual motivo a fraude acontece." |
| 2 | **Logística** | "Pagamos o frete por peso. Quero o histórico diário do peso transportado e saber qual transportadora atrasa." |
| 3 | **Operações** | "Não sei onde o pedido trava. Quero ver o ciclo inteiro: criado, pago, separado, enviado, entregue." |

A modelagem de hoje não tem onde guardar nenhuma dessas respostas. É por aí
que a disciplina começa.

---

## 🧭 Como a disciplina funciona

```
   VOCÊ MODELA                    O SCRIPT CONFERE                VOCÊ VÊ
┌─────────────────┐            ┌─────────────────────┐        ┌──────────────┐
│ lê a demanda    │            │ make historico      │        │              │
│ abre o modelo   │ ─────────► │ make streaming      │ ─────► │  dashboards  │
│ (DBML)          │            │ make etl            │        │  no Metabase │
│ aplica no banco │            │                     │        │              │
└─────────────────┘            │ rodou = está certo  │        └──────────────┘
                               │ parou = diz o que   │
                               │         falta       │
                               └─────────────────────┘
```

1. **O modelo já está desenhado.** Ele está em [`modelagem/dbml/`](./modelagem/dbml/),
   no formato do [dbdiagram.io](https://dbdiagram.io). Você não precisa
   inventar a modelagem: precisa **entendê-la** e **replicá-la no banco**.
2. **O passo a passo te leva pela mão.** Cada etapa explica o motivo de cada
   tabela e de cada coluna antes de mostrar o comando.
3. **Os scripts são a prova.** O gerador de histórico, o streaming e o ETL
   conferem o seu banco contra o modelo antes de rodar. Se você fez certo,
   eles rodam até o fim. Se não, eles param e dizem exatamente o que falta:

```
❌ Modelagem do TRANSACIONAL (OLTP) incompleta. Corrija antes de continuar:

   produtos.peso_gramas         a coluna não existe
   transportes                  a tabela não existe
   carga_pedidos                falta a chave estrangeira (FK) para pedidos(id)
```

4. **Travou?** Toda etapa tem um gabarito (`make gabarito-...`). Use sem culpa,
   mas tente antes.

---

## ✅ Pré-requisitos

* [ ] **Docker** e **Docker Compose v2** (o comando é `docker compose`, com espaço)
* [ ] **`make`** — todos os comandos da trilha começam com ele
* [ ] ~3 GB de RAM livres e ~3 GB de disco para as imagens

> **Você não precisa instalar Python, PostgreSQL nem biblioteca nenhuma.**
> Tudo roda dentro de containers.

### 🪟 Estou no Windows

Siga primeiro o guia **[Preparando o Windows](./docs/windows.md)**. Ele
instala o WSL2, o Docker Desktop e o `make`, e baixa o repositório no lugar
certo. Leva uns 20 minutos, uma vez só.

> ⚠️ No Windows, **todos os comandos da trilha são digitados no terminal do
> Ubuntu (WSL)**, nunca no PowerShell.

Ao terminar o guia, volte para cá e continue do passo
[3. Confira o terreno](#3-confira-o-terreno).

### 🐧 Estou no Linux ou no Mac

Além do Docker, falta só o `make`, que não vem com o Docker e na maioria das
máquinas não vem instalado:

| Sistema | Como instalar |
|---|---|
| Ubuntu / Debian | `sudo apt update && sudo apt install make` |
| Fedora | `sudo dnf install make` |
| Mac | `xcode-select --install` |

No Mac, dê pelo menos 4 GB de memória ao Docker Desktop (Settings →
Resources).

---

## ▶️ Começando em 5 minutos

### 1. Baixe o repositório

```bash
git clone https://github.com/sudoers-ai/jornada_dados_modelagem.git
cd jornada_dados_modelagem
```

(No Windows você já fez isso no [guia de preparação](./docs/windows.md), dentro
do terminal do Ubuntu.)

### 2. Confira se você tem o `make`

<!-- rodar: shell -->
```bash
make --version
```

Tem que aparecer a versão, em algo como:

```text
GNU Make 4.3
```

Se aparecer `make: command not found` (ou `comando não encontrado`):

* **no Windows**, você provavelmente está no PowerShell. Abra o terminal do
  **Ubuntu** e veja o [guia de preparação](./docs/windows.md);
* **no Linux ou no Mac**, instale com o comando da tabela
  [logo acima](#-estou-no-linux-ou-no-mac) e repita este passo.

### 3. Confira o terreno

<!-- rodar: shell -->
```bash
make verificar
```

Ele checa Docker, Compose, portas e memória, e diz em português o que fazer se
algo estiver errado. Saída esperada:

```
Conferindo o ambiente

  ✅ Docker respondendo (29.9.0)
  ✅ Docker Compose v2 (5.6.0)
  ✅ porta 5440 livre (PostgreSQL transacional)
  ✅ porta 5441 livre (PostgreSQL dimensional)
  ✅ porta 3020 livre (Metabase)
  ✅ memória disponível para o Docker: 31 GB

Tudo certo. Próximo passo: make subir
```

> Se alguma porta estiver ocupada, a mensagem diz qual linha do arquivo `.env`
> trocar. Não precisa mexer em mais nada.

### 4. Suba o ambiente

<!-- rodar: shell -->
```bash
make subir
```

Na primeira vez ele baixa as imagens (uns 2 GB) e leva alguns minutos. Você
verá o Docker criando a rede, os volumes e os containers, e no fim:

```
...
  ✅ modelagem_metabase pronto

  Tudo no ar. Continue em modelagem/01_legado/README.md
```

O Metabase é o último a ficar pronto (de 15 segundos a 2 minutos, conforme a
máquina). O comando espera por ele.

### 5. Confira que subiu

<!-- rodar: shell -->
```bash
make status
```

```
NAME                    SERVICE         STATUS
modelagem_dw            postgres_dw     Up 2 minutes (healthy)
modelagem_metabase      metabase        Up 2 minutes (healthy)
modelagem_metabase_db   metabase_db     Up 2 minutes (healthy)
modelagem_oltp          postgres_oltp   Up 2 minutes (healthy)
```

Os quatro precisam estar `healthy`. Se algum não estiver, veja o
[❓ FAQ](./docs/faq.md).

---

## 🚪 O que subiu

| Serviço | Container | Endereço | Credenciais |
|---|---|---|---|
| PostgreSQL **transacional** (OLTP) | `modelagem_oltp` | `localhost:5440`, banco `liga_sudoers` | `sudoers` / `password` |
| PostgreSQL **dimensional** (DW) | `modelagem_dw` | `localhost:5441`, banco `liga_sudoers_dw` | `sudoers` / `password` |
| **Metabase** (dashboards) | `modelagem_metabase` | http://localhost:3020 | `contato@sudoers.com.br` / `*liga01` |

Para entrar nos bancos você não precisa de cliente instalado:

```bash
make psql-oltp     # abre o psql no transacional
make psql-dw       # abre o psql no dimensional
```

Dentro do `psql`, `\dt` lista as tabelas, `\d nome_da_tabela` descreve uma
tabela e `\q` sai.

> As portas fogem do padrão de propósito: assim este repositório convive com
> `liga_sudoers`, `jornada_dados` e `jornada_dados_nosql`, se você os tiver
> rodando.

---

## 🗺️ A trilha

Cada etapa é uma pasta com o seu próprio README. **Siga na ordem** — cada uma
termina dizendo para onde ir.

| # | Etapa | O que você faz | A prova de que deu certo |
|---|---|---|---|
| 1 | [Conhecer o legado](./modelagem/01_legado/README.md) | Explora as 6 tabelas, o DW e os dashboards que existem hoje | Você sabe dizer o que o modelo atual **não** responde |
| 2 | [As três demandas](./modelagem/02_demandas/README.md) | Lê os pedidos da diretoria e o modelo que os atende | Você sabe explicar cada tabela nova |
| 3 | [Evoluir o transacional](./modelagem/03_evolucao_oltp/README.md) | Cria 7 tabelas e 8 colunas no OLTP | `make conferir-oltp` sem pendências |
| 4 | [Histórico e streaming](./data_simulator/README.md) | Roda os geradores de dados | `make historico` e `make streaming` rodam até o fim |
| 5 | [O DW de hoje](./modelagem/04_dw_legado/README.md) | Roda o ETL antigo e descobre onde ele mente | Você encontra o faturamento contado em dobro |
| 6 | [Evoluir o dimensional](./modelagem/05_evolucao_dw/README.md) | Recria o star schema: 7 dimensões e 4 fatos | `make conferir-dw` sem pendências |
| 7 | [O ETL novo](./etl/README.md) | Transforma o transacional em dimensional, passo a passo | `make etl` e `make validar` sem falhas |
| 8 | [Dashboards](./dashboard/README.md) | Conserta os painéis antigos e cria os novos | `make conferir-dashboards` sem pendências |
| 9 | [Desafios](./desafios/desafios.md) | Júnior, Pleno e Sênior | Os seus entregáveis |

Tempo estimado: 6 a 8 horas, que podem ser divididas em várias aulas. O
ambiente guarda o seu progresso entre uma aula e outra.

---

## 📺 Recursos complementares

A playlist [Data Modeling - Jornada Engenheiro de Dados](https://www.youtube.com/watch?v=Kc-mmy8eMcA&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8) mostra, em vídeo, o caminho do transacional ao dashboard no ambiente **antigo** do [`liga_sudoers`](https://github.com/sudoers-ai/liga_sudoers). É o ponto de partida desta disciplina: assista para entender o "antes", e use os roteiros para fazer o "depois". Cada etapa da trilha indica os vídeos que combinam com ela.

- [Data Modeling 01 - Introdução ao ambiente](https://www.youtube.com/watch?v=Kc-mmy8eMcA&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=1)  
- [Mapa Engenharia de Dados 01 - Roadmap de aprendizado](https://www.youtube.com/watch?v=5kRAXMmogT4&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=2)  
- [Data Modeling 02 - DER e ambiente transacional](https://www.youtube.com/watch?v=_fgJFmmQVaU&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=3)  
- [Data Modeling 03 - Entendendo o transacional e suas limitações na modelagem analítica](https://www.youtube.com/watch?v=5o1Dxz91rKY&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=4)  
- [Data Modeling 04 - Dashboards operacionais](https://www.youtube.com/watch?v=ZLtfLNKB3l4&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=5)  
- [Data Modeling 05 - Avançando para uma modelagem dimensional](https://www.youtube.com/watch?v=DZi_7rLBguk&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=6)  
- [Data Modeling 06 - Construindo meu Data Warehouse (DW)](https://www.youtube.com/watch?v=7iB8tvWbVpw&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=7)  
- [Data Modeling 07 - O poder do ETL e do SQL para manipular os dados](https://www.youtube.com/watch?v=DHinno_tFmc&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=8)  
- [Data Modeling 08 - Movendo dados com ETL](https://www.youtube.com/watch?v=QoO1Q0JsrBs&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=9)  
- [Data Modeling 09 - Brincando com as ferramentas de BI](https://www.youtube.com/watch?v=BgMohyMNDxo&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=10)  
- [Data Modeling 10 - Fazendo dashboards analíticos](https://www.youtube.com/watch?v=pW93kToeiUE&list=PLD3-a_5KsN3mBrcfHfB8i3erZf_9eqfw8&index=11)  

Deixe seu like e comentário nos vídeos do YouTube, isso ajuda e incentiva nosso trabalho.

---

## 📚 Material de apoio

* [📐 Do transacional ao dimensional](./docs/modelagem.md) — o texto que explica o **porquê** de tudo
* [📖 Glossário](./docs/glossario.md) — grão, chave substituta, SCD, snapshot... em português claro
* [✅ Checklist do aluno](./docs/checklist.md) — para marcar o que já fez
* [🪟 Preparando o Windows](./docs/windows.md) — WSL2, Docker Desktop e `make`, passo a passo
* [🔎 Validação por evidências](./docs/validacao_evidencia.md) — como provar que cada etapa funcionou
* [❓ FAQ de aula](./docs/faq.md) — erros comuns e como resolver
* [⌨️ Comandos](./docs/comandos.md) — todo `make` e o `docker` equivalente
* [👩‍💻 Perfis e responsabilidades](./docs/perfis.md) — quem faz o quê num time de dados
* [🔗 Integração com os outros repositórios](./integracao/README.md) — **opcional**, para quem cursou as outras partes

---

## 🧰 Comandos do dia a dia

```bash
make ajuda          # lista todos os comandos
make status         # os containers estão no ar?
make validar        # o que está nos bancos está coerente?
make derruba        # para tudo, MANTENDO os dados (use ao fim da aula)
make subir          # volta de onde parou
make limpar         # para tudo e APAGA os dados (recomeça do zero)
make diagnostico    # relatório completo para mandar ao instrutor
```

---

## 🤝 Contribuição

Contribuições são bem-vindas! Abra uma *issue* ou envie um *pull request*.

## 📜 Licença

Este projeto está licenciado sob a **Licença SUDOERS**.

---

# ➡️ Comece em [modelagem/01_legado/README.md](./modelagem/01_legado/README.md)
