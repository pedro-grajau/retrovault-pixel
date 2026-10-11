# Operação local do RetroVault

## Configuração

Backend e comandos carregam `.env` da raiz. Defaults comerciais são próprios da demonstração, independentes do IGDB.

| Variável | Padrão | Efeito |
|---|---:|---|
| CATALOG_INITIAL_PER_PLATFORM | 5 | Amostra inicial por console |
| CATALOG_EXPANSION_PER_PLATFORM | 1 | Novas ofertas por console/execução |
| IMPORT_INTERVAL_SECONDS | 86400 | Agenda IGDB diária |
| SIMULATION_INTERVAL_SECONDS | 1800 | Demanda a cada 30 minutos |
| SIMULATION_BATCH_SIZE | 3 | Máximo de eventos por lote |
| SESSION_TTL_SECONDS | 86400 | Expiração por inatividade |
| SALE_STOCK | 3 | Unidades de venda em nova sessão |
| RENTAL_STOCK | 2 | Exemplares de aluguel em nova sessão |
| SALE_PRICE_CENTS | 9990 | Venda inicial, R$ 99,90 |
| RENTAL_PRICE_CENTS | 1490 | Aluguel inicial, R$ 14,90 |
| RENTAL_DAYS | 7 | Prazo de aluguel |
| CHAT_LIMIT_PER_HOUR | 30 | Mensagens por sessão/hora |

Estoques padrão afetam novas sessões. Importação não redefine preços, estoque ou pedidos existentes. Novas ofertas ficam elegíveis para estoques de novas sessões. O catálogo é global; o comércio é isolado por visitante. Para nova sessão imediata, use janela privada ou remova somente o cookie da demonstração local.

## Importação e scheduler

`make import-initial` autentica no IGDB, resolve os seis consoles e seleciona amostra popular com preferência por variedade de gêneros. `make import` amplia e atualiza metadados. Ausência de capa/descrição tem fallback; preços não vêm da API externa. Identidade jogo IGDB/plataforma é única.

`import_runs` registra running/complete/failed, contagem e erro sanitizado. Trava PostgreSQL impede sobreposição. Há no máximo três tentativas por consulta, espaçamento de 0,30 segundo entre requisições e renovação do token expirado/recusado. A carga é transacional: falhas preservam o catálogo anterior.

`make worker` consulta agendas a cada 30 segundos. Janelas são alinhadas pelo horário Unix, com identidade `scheduled:<número da janela>`. O primeiro processamento da sessão na janela atual pode acontecer logo ao iniciar o worker; os seguintes não reaplicam os efeitos. Dois workers são protegidos por trava. Mantenha o processo ativo para executar agendas locais.

`make tick` consulta uma vez as agendas, útil para verificar operação ou para scheduler externo futuro. Repeti-lo na mesma janela não duplica demanda/importação concluídas. Avançar simulação cria um lote manual distinto, com espera mínima de cinco segundos. Agenda e checkout usam a mesma trava de sessão; eventos respeitam estoque e exemplares.

Worker processa sessões ativas e remove demonstrações expiradas com carrinhos, pedidos e histórico. Catálogo permanece. A interface apresenta os últimos 20 lotes e 100 pedidos; banco persiste todos até expiração. Devoluções automáticas incluem apenas aluguéis da demanda fictícia, preservando o controle do visitante sobre seus aluguéis.

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

Responses API utiliza search_catalog, get_cart, set_cart, prepare_checkout e get_orders. Matching platforms ajuda a esclarecer títulos com várias ofertas. Ferramentas consultam dados atuais e usam os mesmos serviços comerciais do site; não expõem credenciais, conexão, alterações de preço/estoque ou finalização.

Servidor intercepta “Confirmo o pedido” e confirma somente o resumo vigente da própria sessão. Texto do modelo não cria pedido. Há 16 mensagens de contexto, quatro rodadas por resposta, até 1.000 tokens de saída/rodada, timeout de 30 segundos por chamada e uma resposta em andamento por sessão. Chamadas usam `store=false`. Falha ou limite da IA preserva catálogo/carrinho; operações já realizadas continuam visíveis após atualizar estado.

`pixel.chat(sid, message)` é a fronteira do canal. Web obtém sid pelo cookie. Futuro adaptador WhatsApp deve autenticar/mapear conversa para sessão e reutilizar essa operação e os serviços comerciais; não deve aceitar identificadores de sessão vindos do texto. Nenhum webhook WhatsApp faz parte deste MVP.

## Demos externas

`make demos` associa os dois títulos SNES de `backend/demo-links.json`, por título/plataforma. Destinos RetroGames.cc foram verificados; ofertas sem associação não têm botão. Links abrem outra aba e não alteram carrinho/pedido. Pixel indica somente demos cadastradas.

Em 11/10/2026, o iframe de Chrono Trigger foi avaliado no desktop e em viewport de 390 pixels. Exibiu carregamento/publicidade, sem confirmação confiável do jogo iniciado. Por isso `embed_url` fica vazio por padrão. Suporte opcional carrega iframe apenas pelo botão Jogar aqui, com link alternativo e fechamento independente do provedor.

Para nova avaliação local: `PYTHONPATH=backend .venv/bin/python -m retrovault.cli demos --enable-embeds`. Confirme título, carregamento e interação antes de habilitá-lo. `make demos` restaura links como padrão. Demos não são necessárias para vender/alugar; projeto não hospeda arquivos de jogos.
