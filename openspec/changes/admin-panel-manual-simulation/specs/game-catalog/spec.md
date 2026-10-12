# Spec Delta

## Purpose

Disponibilizar ofertas corretas por console e permitir expansão controlada do catálogo por escolha explícita do administrador.

## ADDED Requirements

### Requirement: Catalog by supported platform
O sistema SHALL apresentar ofertas de SNES, GBA, PS1, PS2, PSP e Nintendo DS com busca por título e filtro de plataforma, mantendo identificação e alternativas para metadados ausentes.

#### Scenario: Platform filter
- **WHEN** o visitante seleciona PSP
- **THEN** somente ofertas ativas de PSP aparecem, com identificação da plataforma

#### Scenario: Missing metadata
- **WHEN** um título não tem capa ou descrição
- **THEN** ele permanece identificável com apresentação alternativa

### Requirement: Administrative title selection
O sistema SHALL permitir ao admin buscar títulos no IGDB por nome e plataforma, ver resultados paginados e escolher explicitamente a combinação a adicionar. Buscar ou selecionar não altera o catálogo antes da confirmação.

#### Scenario: Selection confirmed
- **WHEN** o admin escolhe um título compatível com a plataforma e confirma
- **THEN** uma oferta é criada com metadados IGDB e preços fictícios próprios

#### Scenario: Platform mismatch
- **WHEN** a combinação escolhida não é confirmada pelo provedor
- **THEN** a inclusão é recusada sem cadastrar oferta incompatível

#### Scenario: Repeated selection
- **WHEN** uma combinação já cadastrada é confirmada novamente
- **THEN** não há oferta duplicada nem reposição de estoque existente

### Requirement: New offer availability
O sistema MUST disponibilizar novas ofertas com estoque fictício inicial nas sessões ativas e futuras, preservando quantidades, carrinhos e pedidos existentes.

#### Scenario: Existing visitor
- **WHEN** o admin adiciona uma oferta enquanto um visitante está na demonstração
- **THEN** após atualizar o catálogo o visitante pode comprar ou alugar a nova oferta sem reiniciar a sessão

#### Scenario: Concurrent additions
- **WHEN** a mesma oferta é incluída simultaneamente
- **THEN** cada sessão recebe o estoque inicial uma única vez

### Requirement: PSP release relevance
O sistema SHALL priorizar títulos lançados especificamente para PSP nas seleções iniciais e permitir distinguir relançamentos de PS1. Ofertas existentes inadequadas podem ser desativadas pelo admin sem apagar pedidos ou histórico.

#### Scenario: PSP selection
- **WHEN** o admin busca títulos de PSP
- **THEN** pode identificar e escolher lançamentos de PSP sem receber apenas a repetição da seleção de PS1

#### Scenario: Existing offer reviewed
- **WHEN** o admin desativa uma oferta após revisar o catálogo PSP
- **THEN** ela deixa de ser recomendada ou vendida, pedidos antigos permanecem consultáveis e aluguéis existentes podem ser devolvidos

### Requirement: Controlled metadata integration
O sistema MUST acessar IGDB somente no servidor e preservar o catálogo em falhas. A expansão de catálogo SHALL depender de confirmação administrativa, sem execução periódica.

#### Scenario: External failure
- **WHEN** uma busca ou inclusão falha por indisponibilidade do IGDB
- **THEN** o admin recebe erro recuperável, sem inclusão parcial ou exposição de credenciais

#### Scenario: Idle system
- **WHEN** a aplicação fica ativa sem inclusão administrativa
- **THEN** nenhum título é acrescentado automaticamente
