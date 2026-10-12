# Spec Delta

## Purpose

Restringir o painel, o histórico global e a manutenção do catálogo a administradores autenticados.

## ADDED Requirements

### Requirement: Administrator authentication
O sistema SHALL oferecer login e logout administrativos separados da sessão fictícia do visitante, com credenciais verificadas no servidor e prazo de expiração.

#### Scenario: Successful login
- **WHEN** credenciais administrativas válidas são apresentadas
- **THEN** o administrador recebe acesso ao painel sem alterar a sessão de visitante

#### Scenario: Invalid credentials
- **WHEN** credenciais inválidas são apresentadas
- **THEN** o acesso é recusado com mensagem genérica e tentativas repetidas são limitadas

#### Scenario: Expired or revoked session
- **WHEN** uma sessão administrativa expira ou o administrador sai
- **THEN** novas consultas e alterações administrativas exigem novo login

### Requirement: Server-side administrative authorization
O sistema MUST autorizar no servidor cada consulta global e operação de inclusão ou revisão de jogos. Visitantes e ferramentas do Pixel não podem executar essas operações.

#### Scenario: Visitor calls administrative API
- **WHEN** um visitante solicita histórico global ou inclusão de jogo diretamente pela API
- **THEN** a operação é recusada sem divulgar dados administrativos ou modificar o catálogo

#### Scenario: Cross-site mutation
- **WHEN** uma origem não autorizada tenta executar uma alteração administrativa
- **THEN** a alteração é recusada mesmo com cookie administrativo
