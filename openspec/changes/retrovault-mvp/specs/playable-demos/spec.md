# Spec Delta

## Purpose

Permitir experimentar títulos selecionados em serviços externos, preservando a correspondência entre jogo e plataforma e a independência do fluxo comercial simulado.

## ADDED Requirements

### Requirement: Optional demo association
O sistema SHALL associar demonstrações opcionais a uma combinação explícita de jogo e plataforma, apresentando o botão de demonstração apenas quando houver uma associação cadastrada.

#### Scenario: Platform has no demo
- **WHEN** uma oferta de PlayStation 2 não possui demonstração cadastrada, mesmo existindo uma para outra plataforma
- **THEN** essa oferta não apresenta uma demonstração de outra plataforma como equivalente

### Requirement: External demonstration access
O sistema SHALL permitir abrir a demonstração externa cadastrada com identificação do provedor e manter o carrinho e a sessão do visitante disponíveis ao retornar.

#### Scenario: Return from demo
- **WHEN** o visitante abre uma demonstração e retorna ao RetroVault
- **THEN** seu carrinho permanece disponível sem gerar pedidos ou pagamentos

### Requirement: Embedded demo fallback
Se uma demonstração incorporada for habilitada, o sistema MUST oferecer um link externo alternativo e preservar o uso do site quando a incorporação falhar.

#### Scenario: Embed unavailable
- **WHEN** uma demonstração incorporada não pode ser carregada
- **THEN** o visitante dispõe de um link alternativo sem impedir a navegação no catálogo

### Requirement: Independent commercial simulation
O sistema MUST apresentar a demonstração como serviço externo e tratar compra e aluguel como simulações de exemplares físicos, sem prometer acesso digital adquirido pelo pedido.

#### Scenario: Order completed
- **WHEN** o visitante conclui uma locação fictícia
- **THEN** o pedido não é apresentado como concessão ou desbloqueio de acesso ao serviço externo
