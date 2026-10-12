# Spec Delta

## Purpose

Tornar o atendimento do Pixel rastreável desde a conversa e recomendações até alterações de carrinho e pedidos confirmados.

## ADDED Requirements

### Requirement: Complete conversation history
O sistema SHALL preservar as mensagens de cada conversa com identificador, papel, horário e estado da resposta, mantendo o histórico administrativo independente da janela de contexto enviada ao Pixel.

#### Scenario: Long conversation
- **WHEN** uma conversa ultrapassa 16 mensagens
- **THEN** todas as novas mensagens permanecem consultáveis pelo admin, ainda que o contexto do modelo seja limitado

#### Scenario: Provider failure
- **WHEN** o Pixel falha ao responder uma mensagem recebida
- **THEN** a mensagem e a falha ficam registradas sem inventar uma resposta ou ação concluída

### Requirement: Recommendation and action trace
O sistema MUST registrar recomendações estruturadas com jogo e plataforma, alterações efetivas de carrinho, checkout e pedido, com horário, origem Pixel ou interface e vínculos à conversa quando houver.

#### Scenario: Mixed interaction
- **WHEN** Pixel recomenda um título, o visitante o adiciona pela interface e confirma o pedido
- **THEN** o admin vê a recomendação, a inclusão com origem interface e o pedido na jornada da mesma conversa

#### Scenario: Retrieved but not recommended
- **WHEN** uma consulta de catálogo retorna títulos que não foram recomendados pelo Pixel
- **THEN** esses resultados não são contabilizados como recomendações

#### Scenario: Failed action
- **WHEN** uma inclusão ou confirmação é recusada por falta de estoque
- **THEN** a jornada registra a tentativa sem marcar alteração ou pedido como efetivado

### Requirement: Journey progression
O sistema SHALL listar conversas com seu avanço em recomendações, carrinho e pedido, permitindo abrir a linha do tempo e consultar a conversão em cada etapa. Demanda fictícia não conta como conversão de conversa.

#### Scenario: Abandoned cart
- **WHEN** há recomendação e inclusão efetiva sem pedido confirmado
- **THEN** a jornada mostra chegada ao carrinho e ausência de conversão em pedido

#### Scenario: Simulated demand
- **WHEN** um lote de simulação cria um pedido na sessão de uma conversa
- **THEN** ele aparece nas operações comerciais, mas não é atribuído à conversão do Pixel

### Requirement: Honest historical attribution
O sistema MUST identificar registros anteriores ao rastreamento como legado ou origem desconhecida e não inferir recomendações ou causalidade ausentes.

#### Scenario: Legacy conversation
- **WHEN** são migradas as últimas mensagens disponíveis de uma sessão anterior
- **THEN** elas são identificadas como histórico parcial, sem horários originais ou vínculos de recomendação inventados
