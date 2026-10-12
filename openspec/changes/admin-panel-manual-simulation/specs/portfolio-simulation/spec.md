# Spec Delta

## Purpose

Permitir demonstrações controladas por avanço manual, com demanda fictícia verificável e estoques isolados por visitante.

## ADDED Requirements

### Requirement: Fictitious visitor session
O sistema SHALL iniciar uma demonstração com cliente fictício, carrinho e estoque próprios, sem dados pessoais reais, preservando histórico administrativo quando o acesso público expirar.

#### Scenario: Independent visitors
- **WHEN** dois visitantes iniciam demonstrações
- **THEN** cada um recebe carrinho e estoque independentes

### Requirement: Manual simulation only
O sistema SHALL gerar demanda fictícia exclusivamente ao acionar “Avançar simulação”, em lote limitado de vendas, aluguéis e devoluções com resultados visíveis.

#### Scenario: Manual advance
- **WHEN** o visitante aciona o botão
- **THEN** um lote é processado na sessão atual e os eventos realizados ou ignorados são apresentados

#### Scenario: No automatic advance
- **WHEN** um intervalo de tempo passa sem clique
- **THEN** não são criados pedidos, aluguéis ou devoluções pela demanda simulada

### Requirement: Separate catalog management
O sistema SHALL manter “Adicionar jogos” separado de “Avançar simulação”, exibindo busca e inclusão de títulos somente na área administrativa.

#### Scenario: Visitor simulation screen
- **WHEN** um visitante abre a simulação
- **THEN** pode avançar demanda, mas não buscar nem adicionar jogos externos

#### Scenario: Administrative addition
- **WHEN** o admin adiciona um título
- **THEN** nenhuma venda ou locação é gerada como efeito da inclusão

### Requirement: Stock-consistent and isolated demand
O sistema MUST respeitar estoques de venda e aluguel, não repetir efeitos de um mesmo lote e devolver pela demanda apenas exemplares alugados pela própria simulação.

#### Scenario: Retry batch
- **WHEN** um lote já processado é recebido novamente
- **THEN** o resultado anterior é retornado sem novos efeitos comerciais

#### Scenario: Unavailable stock
- **WHEN** o lote tenta vender ou alugar uma oferta sem disponibilidade
- **THEN** registra evento ignorado sem estoque negativo

#### Scenario: Visitor rental
- **WHEN** há um aluguel do visitante e a demanda simula uma devolução
- **THEN** o aluguel do visitante permanece aberto

#### Scenario: Other visitor
- **WHEN** uma sessão avança a demanda
- **THEN** estoque e pedidos de outra sessão permanecem inalterados
