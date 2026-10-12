# Spec Delta

## Purpose

Permitir ao administrador acompanhar vendas, receita simulada e locações a partir do histórico comercial preservado.

## ADDED Requirements

### Requirement: Commercial dashboard
O sistema SHALL apresentar unidades vendidas, receita de vendas, receita de aluguéis, receita total simulada e jogos mais vendidos, filtrados por período, plataforma e autor visitante ou simulação.

#### Scenario: Mixed order
- **WHEN** um pedido confirmado contém duas vendas de R$ 99,90 e um aluguel de R$ 14,90
- **THEN** os indicadores registram duas unidades vendidas, R$ 199,80 em vendas, R$ 14,90 em aluguéis e R$ 214,70 no total

#### Scenario: Uncompleted checkout
- **WHEN** um carrinho ou checkout não resulta em pedido confirmado
- **THEN** ele não incrementa receita ou unidades vendidas

#### Scenario: Filtered results
- **WHEN** o admin seleciona período, plataforma ou autor
- **THEN** todos os indicadores comerciais usam o mesmo recorte e informam que os valores são fictícios

### Requirement: Rental monitoring
O sistema SHALL listar aluguéis com título, plataforma, pedido, sessão fictícia, início, prazo e estado aberto, atrasado ou devolvido; o período considera a data de início do aluguel.

#### Scenario: Returned rental
- **WHEN** um exemplar é devolvido
- **THEN** o painel apresenta o estado devolvido sem somá-lo a aluguéis abertos ou diminuir a receita registrada

#### Scenario: Overdue rental
- **WHEN** o prazo passa e não há devolução registrada
- **THEN** o painel identifica a locação como atrasada

### Requirement: Durable administrative history
O sistema MUST manter pedidos, aluguéis e vínculo com a jornada disponíveis ao admin após expiração da sessão de visitante, sem permitir acesso público ao histórico de outras sessões.

#### Scenario: Visitor session expires
- **WHEN** uma sessão fica inativa além de seu prazo
- **THEN** seu acesso público é encerrado e seu histórico comercial permanece no painel

#### Scenario: Empty dataset
- **WHEN** não há registros no recorte escolhido
- **THEN** o painel exibe indicadores zerados e listas vazias
