# Spec Delta

## Purpose

Permitir compras e aluguéis físicos simulados com estoques separados e comportamento consistente entre o catálogo e o atendimento conversacional.

## ADDED Requirements

### Requirement: Separate stock by modality
O sistema SHALL manter estoque de venda separado dos exemplares de locação para cada jogo e plataforma, impedindo disponibilidade negativa.

#### Scenario: Sale stock does not affect rentals
- **WHEN** um pedido de venda é concluído
- **THEN** apenas o estoque de venda correspondente é reduzido

#### Scenario: Rental availability
- **WHEN** um exemplar é alugado
- **THEN** ele fica indisponível para novas locações até sua devolução

### Requirement: Shared cart
O sistema SHALL disponibilizar um carrinho por sessão, editável tanto pelo catálogo quanto pelo Pixel, com jogo, plataforma, modalidade, quantidade, preço e condições aplicáveis.

#### Scenario: Cross-channel cart edit
- **WHEN** o visitante adiciona um jogo pelo catálogo e pede ao Pixel outro item
- **THEN** o mesmo carrinho contém as duas seleções e ambas aparecem na interface

### Requirement: Explicit order confirmation
O sistema MUST apresentar um resumo atualizado e exigir confirmação explícita do visitante antes de concluir um pedido; alterações posteriores ao resumo invalidam a confirmação anterior.

#### Scenario: Visitor confirms summary
- **WHEN** o visitante confirma um resumo vigente com itens disponíveis
- **THEN** o sistema registra um pedido fictício e aplica suas movimentações de estoque uma única vez

#### Scenario: Summary changes
- **WHEN** um item, preço, prazo ou disponibilidade muda após a apresentação do resumo
- **THEN** o sistema exige novo resumo e nova confirmação

### Requirement: Checkout stock validation
O sistema MUST revalidar preços e disponibilidade na conclusão do pedido e rejeitar itens indisponíveis sem concluir parcialmente o pedido.

#### Scenario: Concurrent final unit requests
- **WHEN** dois pedidos tentam adquirir a última unidade disponível
- **THEN** apenas um pedido é concluído e o outro recebe uma indicação de indisponibilidade

### Requirement: Simulated rentals and returns
O sistema SHALL registrar início, prazo e estado de cada aluguel e permitir uma devolução simulada que restitua a disponibilidade do exemplar uma única vez.

#### Scenario: Return repeated
- **WHEN** a devolução de um aluguel já encerrado é solicitada novamente
- **THEN** o estoque não é incrementado novamente

### Requirement: Fictitious payment
O sistema MUST concluir pedidos por um pagamento explicitamente simulado sem exigir cartão, documento, endereço real ou processar cobranças.

#### Scenario: Simulated payment failure
- **WHEN** o pagamento simulado falha
- **THEN** nenhum pedido concluído ou consumo definitivo de estoque é registrado
