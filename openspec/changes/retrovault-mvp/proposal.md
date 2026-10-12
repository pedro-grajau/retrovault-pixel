# Proposal

## Why

O RetroVault demonstrará, em um portfólio, um agente conversacional que acompanha a escolha de um jogo até uma compra ou locação física simulada. O projeto combina metadados reais de jogos com clientes, estoque, demanda, pedidos e pagamentos fictícios, permitindo experimentar o fluxo completo.

## What Changes

- Criar um site RetroVault com catálogo e chat com o agente Pixel, em português.
- Carregar metadados do IGDB para SNES, GBA, PlayStation 1, PlayStation 2, PSP e Nintendo DS, começando com uma pequena amostra por plataforma e importando novos títulos periodicamente.
- Manter estoques separados de venda e locação, identificando cada oferta por jogo e plataforma.
- Permitir compras e aluguéis pelo catálogo ou pelo Pixel, com carrinho compartilhado e confirmação explícita do visitante.
- Simular clientes, pagamentos, pedidos, retirada e devolução, sem cobranças ou entrega real de jogos.
- Associar demonstrações jogáveis opcionais a títulos e plataformas; avaliar links e incorporação oferecidos pelo RetroGames.cc.
- Gerar demanda fictícia por eventos periódicos e pelo botão “Avançar simulação”.
- Preparar o núcleo conversacional para um adaptador futuro de WhatsApp, sem implementar esse canal no MVP.

Implementação: backend Python/FastAPI e demanda a cada 30 minutos, conforme escolha do usuário. Defaults configuráveis do MVP: cinco jogos por plataforma, aluguel de sete dias, retirada fictícia e expansão diária; detalhes estão no design.

## Capabilities

### New Capabilities

- `game-catalog`: catálogo por plataforma, importação de metadados e atualização periódica pelo IGDB.
- `physical-commerce`: estoques separados, carrinho compartilhado, pedidos de venda e aluguel e devoluções simuladas.
- `pixel-assistant`: conversa orientada a ferramentas para recomendações e operações comerciais.
- `playable-demos`: associação de demonstrações externas opcionais por jogo e plataforma.
- `portfolio-simulation`: sessões fictícias e demanda simulada periódica ou manual.

### Modified Capabilities

Nenhuma. O projeto ainda não possui especificações de capacidades.

## Impact

Aplicação nova: interface web, backend, persistência, integração IGDB, OpenAI com o modelo configurado no ambiente e execução periódica de importações e simulações. Credenciais existentes no `.env` são usadas apenas no servidor, foram validadas sem exposição e o arquivo é ignorado pelo Git.

Fora do MVP: WhatsApp, pagamentos reais, dados pessoais necessários para cadastro, logística real, distribuição de arquivos de jogos e garantia de demonstração jogável para todo o catálogo.
