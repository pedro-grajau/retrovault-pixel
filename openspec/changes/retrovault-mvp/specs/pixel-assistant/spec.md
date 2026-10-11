# Spec Delta

## Purpose

Oferecer atendimento conversacional em português com o Pixel, apoiando recomendações e compras ou aluguéis a partir dos dados e regras do RetroVault.

## ADDED Requirements

### Requirement: Web conversation
O sistema SHALL oferecer chat com Pixel no site, mantendo o contexto da sessão e informando falhas de resposta sem declarar ações inexistentes como concluídas.

#### Scenario: Conversation continues
- **WHEN** o visitante menciona seu console e depois pede uma recomendação
- **THEN** Pixel considera o console já informado na sessão

#### Scenario: AI provider failure
- **WHEN** o provedor de IA não responde
- **THEN** o chat apresenta uma falha recuperável e o catálogo continua utilizável

### Requirement: Grounded recommendations
Pixel MUST basear recomendações comerciais, preços, plataformas e disponibilidade em consultas ao catálogo e às ofertas locais.

#### Scenario: Budget and platform
- **WHEN** o visitante pede um jogo para PSP dentro de um orçamento
- **THEN** Pixel consulta ofertas compatíveis e explica as opções ou a ausência de resultados

#### Scenario: Unknown game
- **WHEN** o visitante pede um título ausente do catálogo
- **THEN** Pixel informa a ausência e não inventa estoque ou preço

### Requirement: Authorized commerce tools
Pixel MUST operar o carrinho e os pedidos pelas mesmas regras do catálogo, exigir confirmação explícita do resumo vigente e acessar apenas a sessão do visitante.

#### Scenario: Prompt attempts to bypass confirmation
- **WHEN** uma mensagem pede para ignorar regras de estoque ou concluir um pedido sem confirmação
- **THEN** as regras comerciais continuam aplicadas e nenhum pedido inválido é concluído

#### Scenario: Other session requested
- **WHEN** o visitante solicita o carrinho ou pedido de outra sessão
- **THEN** o acesso é recusado sem revelar os dados da outra sessão

### Requirement: Clarify ambiguous selection
Pixel SHALL esclarecer plataforma, modalidade ou item quando a seleção for ambígua antes de modificar o carrinho.

#### Scenario: Multiple platforms
- **WHEN** o título solicitado tem ofertas para mais de uma plataforma e o visitante não definiu um console
- **THEN** Pixel pergunta qual plataforma deseja antes de adicionar o item

### Requirement: Demo-aware recommendations
Pixel SHALL oferecer demonstrações apenas para combinações de jogo e plataforma com associação cadastrada, deixando claro que a experiência é externa à locação física.

#### Scenario: Demo not available
- **WHEN** o visitante solicita experimentar um título sem demonstração cadastrada
- **THEN** Pixel informa a ausência sem inventar um endereço
