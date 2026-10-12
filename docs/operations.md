# Operação local do RetroVault

## Configuração

Backend e comandos carregam `.env` da raiz. Defaults comerciais são próprios da demonstração, independentes do IGDB.

Quando `APP_ORIGIN` aponta para loopback, `localhost`, `127.0.0.1` e `[::1]` são aceitos apenas no mesmo protocolo e porta. Uma origem pública continua restrita ao endereço configurado. Após alterar configurações ou código do backend, reinicie `make api`.

| Variável | Padrão | Efeito |
|---|---:|---|
| CATALOG_INITIAL_PER_PLATFORM | 5 | Amostra inicial por console |
| SIMULATION_BATCH_SIZE | 3 | Máximo de eventos por lote |
| SESSION_TTL_SECONDS | 86400 | Expiração por inatividade |
| SALE_STOCK | 3 | Unidades de venda em nova sessão |
| RENTAL_STOCK | 2 | Exemplares de aluguel em nova sessão |
| SALE_PRICE_CENTS | 9990 | Venda inicial, R$ 99,90 |
| RENTAL_PRICE_CENTS | 1490 | Aluguel inicial, R$ 14,90 |
| RENTAL_DAYS | 7 | Prazo de aluguel |
| CHAT_LIMIT_PER_HOUR | 30 | Mensagens por sessão/hora |

Estoques padrão afetam novas sessões e ofertas incluídas pelo admin nas sessões ativas. Inclusões repetidas não repõem estoque. O catálogo é global; o comércio é isolado por visitante.

## Carga inicial e manutenção

`make import-initial` é destinado a catálogo vazio. Resolve os consoles no IGDB e seleciona uma amostra com variedade de gêneros, priorizando lançamentos próprios de PSP. Após essa carga, a expansão depende de busca, seleção e confirmação no painel administrativo. Metadados ausentes têm fallback; preços vêm da configuração fictícia.

`make worker` executa somente manutenção a cada 30 segundos, sem gerar demanda ou importar títulos. `make tick` executa uma rodada de manutenção. Sessões expiradas perdem acesso público, mas seus históricos comerciais e conversacionais são preservados. A interface pública apresenta os últimos 20 lotes e 100 pedidos; o admin consulta registros paginados e totais sem esse limite.

O botão Avançar simulação cria um lote manual com espera mínima de cinco segundos. Lotes repetidos não duplicam efeitos. As regras de estoque e devolução são as mesmas do comércio; devoluções da demanda incluem somente aluguéis da própria demanda fictícia. Apenas o admin adiciona jogos, em ação separada que não produz pedidos.

## Comércio

Preços são inteiros em centavos. Cookie opaco HttpOnly, SameSite=Lax identifica a sessão; o modelo não escolhe o identificador. Em futura implantação HTTPS, configure `COOKIE_SECURE=true` e a origem correspondente.

| Operação | Contrato |
|---|---|
| POST /api/session | Cria persona fictícia ou recupera sessão válida |
| GET /api/catalog?q=&platform= | Ofertas e disponibilidade da sessão |
| GET /api/state | Carrinho, pedidos, histórico e mensagens |
| PUT /api/cart | `{offer_id, mode: "sale" ou "rental", quantity: 0..10}` |
| POST /api/checkout | Prepara resumo, sem pedido |
| POST /api/confirm | `{checkout_id, confirmed: true, payment_success: true}` |
| POST /api/rentals/{id}/return | Devolução idempotente |
| POST /api/simulation | Avanço manual |
| POST /api/chat | `{message}`, até 2.000 caracteres |

Quantidade zero remove item. Preço informado pelo cliente não é aceito. Adicionar não reserva estoque. Resumo dura dez minutos e congela versão, itens, valores, prazo e disponibilidade; mudança exige novo resumo. Pedido guarda os valores; aluguel ocupa exemplar até devolução. Repetição do checkout retorna o pedido existente sem nova movimentação.

`payment_success: false` testa recusa fictícia pela API, sem pedido ou baixa. A interface usa aprovação simulada. Compra e aluguel mistos são atômicos. Checkout e aluguel de outra sessão são recusados. Pedido não concede acesso digital.

Exemplo sem dados pessoais:

```python
import httpx
with httpx.Client(base_url="http://localhost:8000/api") as api:
    api.post("/session", json={}).raise_for_status()
    oferta = api.get("/catalog", params={"platform": "snes"}).json()[0]
    for modalidade in ("sale", "rental"):
        api.put("/cart", json={"offer_id": oferta["id"], "mode": modalidade, "quantity": 1}).raise_for_status()
    resumo = api.post("/checkout", json={}).json()
    api.post("/confirm", json={"checkout_id": resumo["checkout_id"], "confirmed": True}).raise_for_status()
    aluguel = next(o for o in api.get("/state").json()["orders"] if o["actor"] == "visitor")["rentals"][0]
    api.post(f'/rentals/{aluguel["id"]}/return', json={}).raise_for_status()
```

## Pixel e futuro WhatsApp

Responses API utiliza search_catalog, record_recommendations, get_cart, set_cart, prepare_checkout e get_orders. Matching platforms ajuda a esclarecer títulos com várias ofertas. Ferramentas consultam dados atuais e usam os mesmos serviços comerciais do site; não expõem credenciais, conexão, alterações de preço/estoque ou finalização.

Servidor intercepta “Confirmo o pedido” e confirma somente o resumo vigente da própria sessão. Texto do modelo não cria pedido. Há 16 mensagens de contexto, quatro rodadas por resposta, até 1.000 tokens de saída/rodada, timeout de 30 segundos por chamada e uma resposta em andamento por sessão. Chamadas usam `store=false`. Falha ou limite da IA preserva catálogo/carrinho; operações já realizadas continuam visíveis após atualizar estado.

`pixel.chat(sid, message)` é a fronteira do canal. Web obtém sid pelo cookie. Futuro adaptador WhatsApp deve autenticar/mapear conversa para sessão e reutilizar essa operação e os serviços comerciais; não deve aceitar identificadores de sessão vindos do texto. Nenhum webhook WhatsApp faz parte deste MVP.

## Demos externas

`make demos` associa os dois títulos SNES de `backend/demo-links.json`, por título/plataforma. Destinos RetroGames.cc foram verificados; ofertas sem associação não têm botão. Links abrem outra aba e não alteram carrinho/pedido. Pixel indica somente demos cadastradas.

Em 11/10/2026, o iframe de Chrono Trigger foi avaliado no desktop e em viewport de 390 pixels. Exibiu carregamento/publicidade, sem confirmação confiável do jogo iniciado. Por isso `embed_url` fica vazio por padrão. Suporte opcional carrega iframe apenas pelo botão Jogar aqui, com link alternativo e fechamento independente do provedor.

Para nova avaliação local: `PYTHONPATH=backend .venv/bin/python -m retrovault.cli demos --enable-embeds`. Confirme título, carregamento e interação antes de habilitá-lo. `make demos` restaura links como padrão. Demos não são necessárias para vender/alugar; projeto não hospeda arquivos de jogos.

## Histórico administrativo e expiração

O acesso público expira por inatividade. O worker de manutenção marca a sessão como expirada e limpa carrinho, checkouts não consumidos e estoque temporário sem apagar pedidos, aluguéis, conversas ou eventos. Exemplares referenciados por aluguéis permanecem no banco. A limpeza ocorre uma única vez por sessão.

A migração 003 é aditiva. Mensagens anteriores disponíveis são marcadas como legado parcial, com horário original desconhecido; mensagens já descartadas não são reconstruídas. Antes de atualizar, mantenha backup do PostgreSQL e confira contagens e totais. Em rollback, pare o worker e mantenha a migração; nunca execute o worker antigo, que apaga sessões em cascata e reativa agendas. Não remova as tabelas de histórico nem reaplique lotes.

## Login administrativo

Configure `ADMIN_USERNAME` e `ADMIN_PASSWORD_HASH` apenas no `.env` do servidor. Gere o hash com `PYTHONPATH=backend .venv/bin/python -c 'import getpass; from retrovault.admin_auth import password_hash; print(password_hash(getpass.getpass()))'`; a senha é lida sem eco e não entra no histórico do shell. O formato é `scrypt$salt$digest`. Não versione senha, hash ou cookies. Sem credenciais configuradas nenhum login é aceito.

O acesso fica em `/admin`. `ADMIN_SESSION_TTL_SECONDS` vale 28800 por padrão; cinco tentativas inválidas por endereço bloqueiam novas tentativas por 15 minutos. A sessão administrativa usa cookie HttpOnly distinto, com logout revogável no banco. Em ambiente HTTPS use `COOKIE_SECURE=true`. Dados globais e catálogo administrativo exigem autenticação no servidor; o cookie de visitante não concede esse acesso.

## Indicadores e jornada

Receita simulada vem dos itens congelados de pedidos confirmados: quantidade vendida, subtotal de venda, subtotal de aluguel e soma dos dois. Carrinhos e checkouts não contam como receita. Devoluções não estornam valores. Período comercial usa criação do pedido; o período de locações usa seu início. Datas informadas no painel incluem o dia final e são interpretadas em America/Fortaleza, convertidas para limites UTC. Autor (`visitor`/`simulation`) distingue demanda; canal (`pixel`/`interface`/`legacy`) distingue origem da confirmação.

As etapas da jornada contam conversas distintas iniciadas no período: recomendação estruturada, inclusão efetiva com quantidade positiva no carrinho e pedido confirmado do visitante. Cada etapa pode ocorrer sem a anterior; eventos posteriores ao período ainda fazem parte da conversa. Conversão é conversas com pedido / conversas iniciadas, não pedidos / recomendações. Eventos de demanda fictícia não entram. A linha do tempo mostra sequência, sem provar causalidade. Busca de catálogo não conta como recomendação; falhas não contam como etapa concluída. Novas mensagens são preservadas integralmente, enquanto o contexto enviado ao Pixel continua limitado. Históricos migrados têm marcação parcial/legado.

## Catálogo administrativo e PSP

No admin, abra Catálogo, escolha console e busque um título. A busca não altera o acervo. Abra os detalhes e confirme a inclusão; o servidor reconsulta a associação jogo/plataforma no IGDB e aplica preços/estoque fictícios configurados. Novas ofertas ficam disponíveis após atualização nas sessões ativas e em sessões futuras. Confirmar uma oferta existente não repõe estoque.

A revisão PSP identifica lançamento próprio, relançamento/port e classificação incerta. As datas por plataforma e `game_type.type` são evidência; ausência de datas não implica lançamento próprio. Fixtures sanitizadas consultadas em 12/10/2026 incluem Patapon, Crisis Core, Final Fantasy VII e Symphony of the Night. Referência: https://api-docs.igdb.com/#game e https://api-docs.igdb.com/#release-date. A revisão não desativa nada automaticamente: o admin confirma cada desativação; pedidos e aluguéis históricos permanecem disponíveis. Itens desativados devem ser removidos do carrinho antes de novo checkout.

Expansão pela CLI foi retirada. `import --initial` é manutenção exclusiva da carga inicial em catálogo vazio; alterações posteriores usam o painel autenticado. O worker não consulta IGDB nem gera demanda. As ferramentas de Pixel não incluem gerenciamento do catálogo.
