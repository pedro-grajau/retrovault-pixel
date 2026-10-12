# Proposal

## Why

O RetroVault precisa de uma visão administrativa durável das operações e do caminho entre atendimento do Pixel e pedido. A execução automática dificulta controlar a demonstração, e a seleção atual do PSP repete principalmente títulos de PS1.

## What Changes

- Criar área `/admin` com login, dashboard de compras, receita simulada e aluguéis, com filtros de período e origem.
- Preservar conversas completas e eventos para acompanhar conversa → recomendações → carrinho → pedido, inclusive ações alternadas entre Pixel e interface.
- Preservar histórico comercial após expiração da sessão de visitante, mantendo isolamento e acesso administrativo protegido.
- **BREAKING** Remover demanda e expansão de catálogo agendadas; visitantes continuam avançando demanda somente pelo botão.
- Disponibilizar ao admin busca no IGDB, seleção explícita de título e plataforma e inclusão no catálogo, separada do avanço de demanda.
- Inicializar estoque das novas ofertas nas sessões ativas, sem repor ofertas existentes.
- Priorizar lançamentos próprios de PSP e revisar ofertas existentes sem apagar referências históricas.

## Capabilities

### New Capabilities

- `admin-access`: login, sessão e autorização administrativa.
- `admin-dashboard`: indicadores e consultas administrativas do histórico comercial.
- `pixel-journey`: histórico completo e rastreabilidade do atendimento até o pedido.
- `game-catalog`: catálogo por plataforma, inclusão manual administrativa e revisão de PSP.
- `portfolio-simulation`: avanço exclusivamente manual e preservação do histórico das sessões.

### Modified Capabilities

Nenhuma capacidade está publicada em `openspec/specs/`. `game-catalog` e `portfolio-simulation` reutilizam os nomes da mudança concluída `retrovault-mvp`, ainda não arquivada. Esta mudança declara o contrato atualizado nesses caminhos; ao arquivar, reconciliar os requisitos do MVP sem restaurar agendas removidas.

## Impact

Frontend Next.js: área administrativa e fluxo de simulação. Backend FastAPI: autenticação, consultas agregadas, busca e importação IGDB, rastreamento das operações. PostgreSQL: migrações para histórico durável, eventos e sessões administrativas. Worker: somente manutenção de sessões; configuração, testes e documentação deixam de anunciar agendas. Não haverá pagamentos reais, WhatsApp, publicação ou cadastro manual de jogos sem metadados IGDB nesta mudança.
