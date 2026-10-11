# RetroVault · Pixel

Locadora física fictícia para portfólio. Compre, alugue e simule devoluções pelo catálogo ou pelo chat Pixel. Metadados vêm do IGDB; clientes, preços, estoque, demanda, pedidos, retirada e pagamentos são fictícios. Não há cobrança, cadastro com dados pessoais ou entrega real de jogos.

Backend **Python 3.12 / FastAPI**, interface Next.js / TypeScript e PostgreSQL 17 em Docker. Um worker Python executa a demanda a cada **30 minutos**, com avanço manual. Publicação e WhatsApp serão etapas posteriores.

## Executar localmente

Requisitos: Python 3.12, Node.js 22, npm e Docker Compose. Execute a partir da raiz do repositório.

Configure `.env` com os nomes de `.env.example`, preservando as credenciais existentes. Não substitua seu arquivo por um exemplo vazio. Chaves IGDB e OpenAI ficam exclusivamente no backend. `PIXEL_OPENAI_MODEL_SNAPSHOT` deve indicar um modelo disponível na sua conta, com ferramentas e Responses API. O modelo local foi validado sem trocar sua configuração.

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
npm ci --prefix frontend
docker compose up -d db
make migrate
make import-initial
make demos
```

A amostra importa cinco ofertas por console: SNES, GBA, PS1, PS2, PSP e NDS. Repetir `make import-initial` atualiza metadados sem duplicar ou ampliar uma amostra preenchida. `make import` acrescenta um jogo por console. Não são baixados ROMs ou executáveis.

Inicie cada processo em seu próprio terminal:

```bash
make api
```

```bash
npm run dev --prefix frontend
```

```bash
make worker
```

Abra [RetroVault](http://localhost:3000) e [documentação da API](http://localhost:8000/docs). Use `localhost`, conforme `APP_ORIGIN`. A interface encaminha `/api` ao backend; `BACKEND_URL` é uma configuração de servidor. PostgreSQL fica no loopback, porta 55432, com volume persistente; credenciais do Compose servem apenas ao desenvolvimento local.

Encerre processos com Ctrl+C e o banco com `docker compose stop db`; o catálogo permanece no volume. Reiniciar não reaplica lotes já concluídos.

## Demonstração

1. Filtre um console e use Comprar ou Alugar. Os botões e o Pixel editam o mesmo carrinho.
2. Pergunte: “Tenho SNES e quero alugar um RPG por até R$ 20”.
3. Peça que adicione uma opção e prepare o resumo. Confira plataforma, modalidade, preço, prazo e retirada.
4. Confirme pelo botão ou feche o resumo e envie exatamente “Confirmo o pedido”. Nenhum cartão é solicitado.
5. Em Meus pedidos, use Simular devolução. Em Simulação, use Avançar simulação e consulte os eventos.

Adicionar não reserva estoque. Mudanças nas condições de um resumo exigem outro. Sessões têm estoques separados; janela privada cria uma demonstração independente.

Chrono Trigger e Super Metroid para SNES têm links externos em `backend/demo-links.json`; o carrinho permanece ao retornar. Iframes são opcionais e estão desabilitados por padrão: o teste exibiu carregamento/publicidade do provedor sem confirmar o jogo iniciado. Procedimentos e fallback: [operações](docs/operations.md).

## Configuração e verificação

`SIMULATION_INTERVAL_SECONDS=1800` controla a meia hora; `IMPORT_INTERVAL_SECONDS=86400` controla a expansão diária. Reinicie backend e worker após alterar `.env`. Consulte [parâmetros e contratos](docs/operations.md).

```bash
make test
npm run build --prefix frontend
npm run typecheck --prefix frontend
```

Testes criam schemas PostgreSQL descartáveis, separados da demonstração. Verificações externas opcionais:

```bash
make verify-clean  # IGDB real em schema vazio, removido ao final
make smoke         # conversa real; consome chamadas/tokens OpenAI
```

O smoke pressupõe os preços padrão e API em execução. Resultados e evidências: [verificação do MVP](docs/verification.md). Acompanhamento: `openspec/changes/retrovault-mvp/`.
