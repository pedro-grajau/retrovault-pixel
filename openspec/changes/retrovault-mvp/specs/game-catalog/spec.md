# Spec Delta

## Purpose

Disponibilizar um catálogo de jogos por plataforma com metadados do IGDB e ampliação periódica, sustentando a navegação e as recomendações do Pixel.

## ADDED Requirements

### Requirement: Catalog by supported platform
O sistema SHALL apresentar uma amostra de jogos de SNES, GBA, PlayStation 1, PlayStation 2, PSP e Nintendo DS, permitindo filtrar por plataforma e buscar por título.

#### Scenario: Platform filter
- **WHEN** o visitante seleciona GBA
- **THEN** o catálogo apresenta ofertas de GBA e identifica a plataforma de cada resultado

#### Scenario: No matches
- **WHEN** uma busca não encontra um título no catálogo local
- **THEN** o sistema informa a ausência sem inventar disponibilidade

### Requirement: IGDB metadata import
O sistema SHALL importar título, identificador IGDB, plataformas e metadados disponíveis, como descrição, capa e gêneros, mantendo preços e estoques como dados fictícios próprios.

#### Scenario: Missing metadata
- **WHEN** um jogo importado não possui capa ou descrição
- **THEN** o catálogo utiliza uma apresentação alternativa e preserva a identificação do jogo

### Requirement: Periodic catalog expansion
O sistema SHALL executar importações periódicas configuráveis e evitar ofertas duplicadas para a mesma combinação de jogo IGDB e plataforma.

#### Scenario: Repeated import
- **WHEN** a importação reencontra um jogo já cadastrado para a mesma plataforma
- **THEN** seus metadados podem ser atualizados sem duplicar a oferta ou substituir estoque e preços locais

#### Scenario: New title
- **WHEN** uma importação encontra um novo título elegível
- **THEN** o sistema acrescenta a oferta com dados comerciais fictícios e registra o resultado da importação

### Requirement: Server-side credentials and availability
O sistema MUST acessar o IGDB com credenciais apenas no servidor e manter o catálogo já importado acessível em caso de indisponibilidade externa.

#### Scenario: IGDB failure
- **WHEN** a API recusa ou falha em uma importação
- **THEN** o sistema preserva o catálogo existente e registra uma falha sem expor credenciais
