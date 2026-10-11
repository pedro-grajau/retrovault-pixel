# Spec Delta

## Purpose

Demonstrar a operação de uma locadora fictícia por sessões de visitantes e eventos de demanda simulada, com avanço periódico ou manual e efeitos verificáveis no estoque.

## ADDED Requirements

### Requirement: Fictitious customer session
O sistema SHALL permitir iniciar uma sessão de demonstração com um cliente fictício sem exigir cadastro ou dados pessoais reais.

#### Scenario: Start demonstration
- **WHEN** o visitante inicia a demonstração
- **THEN** recebe uma sessão com cliente fictício, carrinho próprio e indicação de que as operações são simuladas

### Requirement: Periodic and manual simulation
O sistema SHALL gerar eventos de demanda em intervalos configuráveis e pelo botão “Avançar simulação”, informando os resultados de cada avanço.

#### Scenario: Manual advance
- **WHEN** o visitante aciona “Avançar simulação”
- **THEN** o sistema processa um lote limitado de eventos e apresenta vendas, aluguéis ou devoluções efetivados ou a ausência de eventos elegíveis

#### Scenario: Scheduled advance
- **WHEN** um intervalo agendado é processado
- **THEN** o sistema aplica eventos pelas mesmas regras usadas no avanço manual

### Requirement: Stock-consistent demand
Eventos fictícios MUST respeitar estoques separados e regras de pedidos e devoluções, sem duplicar efeitos quando uma execução é repetida.

#### Scenario: No rental copies available
- **WHEN** um evento tenta alugar um jogo sem exemplares disponíveis
- **THEN** nenhuma disponibilidade negativa ou locação inválida é criada

#### Scenario: Retry event batch
- **WHEN** o mesmo lote é recebido novamente
- **THEN** seus efeitos comerciais não são aplicados duas vezes

### Requirement: Session isolation
O sistema MUST isolar carrinhos, pedidos e eventos de cada sessão de demonstração para que o avanço de um visitante não modifique os dados de outro.

#### Scenario: Two independent demonstrations
- **WHEN** um visitante avança sua simulação
- **THEN** os pedidos e a disponibilidade da sessão de outro visitante permanecem inalterados

### Requirement: Simulation visibility
O sistema SHALL identificar operações e demanda como fictícias e permitir consultar um histórico resumido dos eventos da sessão sem expor segredos de integrações.

#### Scenario: Event history
- **WHEN** o visitante consulta os eventos de sua demonstração
- **THEN** encontra as movimentações simuladas e seus resultados com identificação da modalidade e da oferta afetada
