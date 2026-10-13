# 2️⃣ As três demandas

> ⬅️ Anterior: [1. Conhecer o legado](../01_legado/README.md) · [README principal](../../README.md) · Etapa 2 de 9

Nesta etapa você ainda **não digita nenhum comando**. Você lê. Modelagem é,
antes de tudo, entender o negócio: uma tabela mal pensada custa muito mais
caro depois que tem dado dentro.

Para cada demanda, este roteiro mostra o pedido como ele chegou, por que o
modelo de hoje não responde, e o que precisa mudar. Leia com o diagrama
aberto ao lado.

---

## O modelo que você vai construir

O time de arquitetura já desenhou a evolução. Ela está em
[`modelagem/dbml/02_oltp_evoluido.dbml`](../dbml/02_oltp_evoluido.dbml):

![Transacional evoluído](../img/02_oltp_evoluido.svg "As 6 tabelas do legado (azul) e as 7 novas (verde)")

> Para navegar com zoom, cole o conteúdo do arquivo `.dbml` em
> [dbdiagram.io/d](https://dbdiagram.io/d). **Faça isso agora** e deixe a aba
> aberta: você vai consultar o diagrama durante toda a etapa 3.

### Como ler o arquivo de modelo

O `.dbml` é texto simples. Veja um trecho:

```
Table transportes [headercolor: #2D6512] {
  id integer [pk, increment]
  id_transportadora integer [not null]
  placa varchar(8) [not null]
  peso_total_gramas integer [not null, default: 0]
  dt_entrega timestamp [note: 'nulo enquanto o caminhao esta em transito']
}

Ref: transportes.id_transportadora > transportadoras.id
```

| No modelo | Significa | No PostgreSQL vira |
|---|---|---|
| `[headercolor: #2D6512]` | tabela **nova** (cabeçalho verde no diagrama) | `CREATE TABLE` |
| `note: 'NOVO ...'` numa coluna | coluna **nova** numa tabela que já existia | `ALTER TABLE ... ADD COLUMN` |
| `pk` | chave primária | `PRIMARY KEY` |
| `increment` | o banco gera o número sozinho | tipo `serial` |
| `not null` | o campo é obrigatório | `NOT NULL` |
| sem `not null` | o campo **pode** ficar vazio | (nada) |
| `default: 0` | valor usado quando ninguém informa | `DEFAULT 0` |
| `unique` | não pode repetir | `UNIQUE` |
| `Ref: a.x > b.y` | chave estrangeira: `a.x` aponta para `b.y` | `REFERENCES b (y)` |
| `indexes { (a, b) [pk] }` | chave primária composta por duas colunas | `PRIMARY KEY (a, b)` |

Guarde esta tabela. Ela é o dicionário entre o desenho e o banco.

---

## Demanda 1 — Antifraude

> **Como chegou:** "Clientes estão reclamando de compras que não fizeram.
> Dizem que o aparelho ou a região não batem com o perfil deles. Hoje não
> temos como marcar um pedido como fraude nem dizer por quê."

**O que o negócio já sabe sobre fraude:**

* **Geolocalização.** A Liga Sudoers só vende em SP, MG e RJ. Compra feita de
  qualquer outro estado é suspeita.
* **Troca de dispositivo.** O cliente sempre comprou de um aparelho e, de
  repente, compra de outro.
* **Dispositivo compartilhado.** Várias contas diferentes comprando do
  **mesmo aparelho físico**. É o chamado *anel de fraude* — o mais difícil de
  ver, porque cada pedido, olhado sozinho, parece normal.

**Por que o modelo de hoje não responde:**

| Problema | Consequência |
|---|---|
| Não existe onde marcar "é fraude" | A fraude confirmada some: ninguém consegue contar nem treinar um modelo |
| O aparelho é um **texto** (`dispositivo = 'iPhone 15'`) | Dois clientes com iPhone 15 são indistinguíveis de um aparelho usado por duas contas |
| O estado está escondido no `geohash` | Para saber a UF é preciso decodificar um código em toda consulta |

**O que muda no transacional:**

| Objeto | Mudança | Para quê |
|---|---|---|
| `dispositivos` | **tabela nova**: `device_id`, `modelo`, `sistema` | O aparelho passa a ter identidade própria. `device_id` é a "impressão digital" do aparelho físico |
| `auditoria_pedidos.device_id` | coluna nova, chave estrangeira para `dispositivos` | Liga cada compra ao aparelho físico usado |
| `auditoria_pedidos.uf` | coluna nova | A UF da compra, já decodificada |
| `auditoria_pedidos.is_fraude` | coluna nova, `false` por padrão | A fraude **confirmada** |
| `auditoria_pedidos.motivo_fraude` | coluna nova | Qual das três regras foi violada |
| `auditoria_pedidos.dt_fraude` | coluna nova | Quando a fraude foi confirmada |

> **A lição de modelagem aqui:** `dispositivo` (o modelo, "iPhone 15") e
> `device_id` (o aparelho físico, `d-855b6c5b`) parecem a mesma coisa e não
> são. Enquanto o aparelho era um atributo de texto, o anel de fraude era
> invisível. No momento em que ele vira uma **entidade** — uma tabela, com
> chave —, "quantas contas usaram este aparelho?" passa a ser uma pergunta
> que o banco sabe responder.
>
> Regra prática: **aquilo que você quer ver compartilhado entre registros
> precisa ser uma tabela, não uma coluna de texto.**

Repare também que a fraude **não é conhecida na hora da compra**. O pedido
nasce com `is_fraude = false`, e dias depois um analista confirma. Isso é um
`UPDATE` — e vai importar muito quando o dado for para o DW.

---

## Demanda 2 — Logística e custo de frete

> **Como chegou:** "Pagamos o transporte por peso e queremos renegociar com
> as transportadoras. Preciso do histórico diário do peso que mandamos e de
> saber quem entrega no prazo. Hoje nem registramos em qual caminhão o pedido
> foi."

**Por que o modelo de hoje não responde:** não existe peso, endereço,
transportadora, caminhão nem data de entrega. O pedido "acaba" quando é
vendido.

**O que muda no transacional:**

| Objeto | Mudança | Para quê |
|---|---|---|
| `produtos.peso_gramas` | coluna nova | O frete é pago por peso |
| `enderecos` | **tabela nova** | Uma pessoa pode ter vários endereços, e pode **se mudar** |
| `pedidos.id_endereco_entrega` | coluna nova, chave estrangeira para `enderecos` | Para onde aquele pedido vai |
| `transportadoras` | **tabela nova**: `nome`, `cnpj`, `custo_por_kg` | Quem transporta, e quanto cobra |
| `transportes` | **tabela nova** | Um caminhão numa viagem: quando saiu, quando deveria chegar, quando chegou, quanto pesava, quanto custou |
| `carga_pedidos` | **tabela nova** | Quais pedidos foram em qual caminhão |

Três decisões de modelagem para você observar no diagrama:

**1. Por que `enderecos` é uma tabela, e não colunas em `pessoas`?**
Porque a relação é **um para muitos**: uma pessoa, vários endereços (casa,
trabalho, o antigo, o novo). Se o endereço fosse coluna de `pessoas`, só
caberia um — e ao mudar de cidade o endereço antigo seria apagado. Com a
tabela, o antigo fica (`is_principal = false`) e o novo entra.

**2. Por que o pedido aponta para um endereço, e não para a pessoa?**
O pedido já aponta para a pessoa (`id_pessoa`). Mas a pessoa pode se mudar
depois da compra. O pedido precisa lembrar **para onde ele foi de fato**.

**3. Por que existe a tabela `carga_pedidos`?**
Um caminhão leva vários pedidos. E, pelo modelo, um pedido pode embarcar em
mais de um caminhão (uma segunda tentativa de entrega, por exemplo). Isso é
uma relação **muitos para muitos (N:N)**, e banco relacional não tem como
representá-la com uma coluna só. A saída é sempre a mesma: uma **tabela
associativa**, cuja chave primária é o par (`id_transporte`, `id_pedido`).

---

## Demanda 3 — Ciclo de vida do pedido

> **Como chegou:** "O cliente liga perguntando do pedido e a gente não sabe
> responder. Também não sei onde o processo trava: é no pagamento? Na
> separação? Na estrada?"

**Por que o modelo de hoje não responde:** o pedido tem uma data de venda e
um valor. Mais nada. Não se sabe nem se foi pago.

**O que muda no transacional:**

| Objeto | Mudança | Para quê |
|---|---|---|
| `pedidos.status` | coluna nova, `'criado'` por padrão | A situação **atual** do pedido |
| `status_pedidos` | **tabela nova**: `id_pedido`, `status`, `dt_evento` | O **histórico**: uma linha para cada mudança de situação |
| `pagamentos` | **tabela nova** | Forma de pagamento, parcelas, se foi aprovado e quando |

As situações possíveis de um pedido:

```
criado ──► pago ──► separado ──► enviado ──► entregue ──► (devolvido)
   │         │          │
   └─────────┴──────────┴──► cancelado
```

**Por que guardar o status em dois lugares?** Parece duplicação, mas são duas
perguntas diferentes:

* `pedidos.status` responde **"como está agora?"** — rápido, sem `JOIN`. É o
  que a tela do atendente usa.
* `status_pedidos` responde **"o que aconteceu e quando?"** — é o que permite
  medir quanto tempo cada etapa leva.

O transacional guarda o **estado atual** e, quando o negócio exige, uma
**trilha de eventos**. Você vai ver na etapa 7 que essa tabela de eventos, tão
natural aqui, precisa mudar completamente de forma para servir à análise.

---

## Resumo: o que você vai criar

| Demanda | Tabelas novas | Colunas novas em tabelas existentes |
|---|---|---|
| 1. Antifraude | `dispositivos` | 5 em `auditoria_pedidos` |
| 2. Logística | `enderecos`, `transportadoras`, `transportes`, `carga_pedidos` | 1 em `produtos`, 1 em `pedidos` |
| 3. Ciclo do pedido | `status_pedidos`, `pagamentos` | 1 em `pedidos` |
| **Total** | **7 tabelas** | **8 colunas** |

As 6 tabelas que já existiam **continuam existindo, com todas as colunas que
tinham**. Nada é apagado nem renomeado. Isso não é acaso: num sistema em
produção existem aplicações lendo essas tabelas agora. Evoluir um modelo
transacional é quase sempre **acrescentar**, raramente trocar.

---

## ✅ Antes de seguir

* [ ] Colei o `02_oltp_evoluido.dbml` no dbdiagram.io e estou com o diagrama aberto
* [ ] Sei a diferença entre `dispositivo` e `device_id`
* [ ] Sei explicar por que `enderecos` e `carga_pedidos` são tabelas
* [ ] Sei por que o status aparece em `pedidos` **e** em `status_pedidos`
* [ ] Sei ler `pk`, `not null`, `default` e `Ref:` no arquivo de modelo

---

# ➡️ Continue em [modelagem/03_evolucao_oltp/README.md](../03_evolucao_oltp/README.md)
