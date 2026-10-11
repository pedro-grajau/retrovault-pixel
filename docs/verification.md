# Verificação do MVP · 11/10/2026

## Ambiente e reprodução

Python 3.12.3, Node.js 22.23.3, PostgreSQL 17 local em Docker e Next.js 16.4.0. Backend FastAPI; modelo OpenAI configurado no `.env` validado na conta local. Segredos não foram impressos, copiados para interface ou incluídos nos artefatos.

Instalação limpa verificada com `backend/requirements.lock` em um novo ambiente virtual e `npm ci` em uma pasta temporária. O build da interface passou nessa pasta. O comando `make verify-clean` criou um schema vazio, aplicou migrações, carregou 30 ofertas reais IGDB, repetiu a carga com zero adições e executou expansão agendada de seis ofertas. Repetir a mesma janela não duplicou importação ou demanda; o schema de QA foi removido ao final.

## Jornadas reais

- Catálogo cobre SNES, GBA, PS1, PS2, PSP e NDS. A demonstração local contém 36 ofertas após expansão. Busca sem resultados exibe mensagem de ausência.
- Super Mario World sem capa/descrição exibiu identificação alternativa e descrição de ausência. Metadados públicos originais foram restaurados após QA.
- Interface: aluguel de Super Mario World, confirmação explícita, pedido persistido e devolução. Depois, carrinho misto de compra de Super Mario World e aluguel de Chrono Trigger, total R$ 114,80, confirmado na interface móvel.
- Pixel real: esclareceu PSP/PS1 ao solicitar Final Fantasy VII sem console; informou título inexistente e ausência sob orçamento R$ 1; recusou ignorar estoque/confirmar sem consentimento; recomendou RPGs SNES sob R$ 20; adicionou Chrono Trigger ao carrinho já editado pelo catálogo; preparou resumo misto e confirmou após “Confirmo o pedido”. Devolução repetida não duplicou disponibilidade. Transcrição sanitizada em [pixel-smoke.json](pixel-smoke.json).
- Worker real: tick com intervalo 1.800 segundos, sessões ativas e importação já processada. Botão manual apresentou histórico de aluguel, venda e devolução. Testes controlam horários das janelas para verificar meia hora sem depender de espera real.
- Destinos de Chrono Trigger e Super Metroid no RetroGames.cc exibiram título/plataforma corretos. Abrir outra aba e retornar preservou o carrinho e não criou pedido. Iframe de Chrono Trigger testado no desktop e em frame de 390 pixels, com link alternativo visível e modal fechável. Não foi confirmado jogo iniciado: incorporações permaneceram desabilitadas por padrão.
- Layout móvel testado em frame real de 390 × 844: documento de 375 pixels úteis, incluindo barra vertical, com scrollWidth igual a clientWidth. Filtros, busca, detalhes, carrinho misto e confirmação sem rolagem horizontal. A interface oferece atalho móvel para o Pixel.

## Testes automatizados

`make test`: **15 testes aprovados**. Verificam migrações/uniquidade, metadados ausentes, importação repetida, falhas imediatas/parciais IGDB, preservação comercial, isolamento, estoque separado, pagamento fictício falho, resumo desatualizado, última unidade concorrente, pedidos mistos, devoluções idempotentes, demanda sem estoque, lotes repetidos, devoluções somente de pedidos simulados, agenda/expiração, ferramentas Pixel, falha/limite IA, origem HTTP e concorrência checkout/simulação.

`npm run build --prefix frontend` e `npm run typecheck --prefix frontend` verificam interface e tipos. TypeScript está em modo estrito. O TestClient apresentou um aviso de depreciação de integração com httpx; os testes de contrato passaram.

## Limites desta entrega

Execução local; não houve publicação, conexão WhatsApp ou gateway de pagamento. Agendas exigem worker ativo. Demonstrações externas têm cobertura selecionada e dependem do provedor. Texto do modelo pode variar; estado comercial definitivo é sempre validado no backend. Novas ofertas recebem estoque apenas em novas sessões, preservando a demonstração em curso.

Prévias: [desktop](retrovault-desktop.png) e [móvel](retrovault-mobile.png). Procedimentos: [README](../README.md) e [operações](operations.md).
