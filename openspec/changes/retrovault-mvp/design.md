# Design

## Context

O repositório contém README e configuração OpenSpec, sem aplicação existente. A motivação e as capacidades estão em `proposal.md`; os contratos de comportamento estão nas cinco especificações desta mudança. Existem nomes de variáveis para IGDB e IA no `.env`; sua presença não comprova validade das credenciais.

Este documento registra a arquitetura implementada e seus defaults configuráveis. Em 11/10/2026, o usuário escolheu Python no backend e demanda periódica a cada 30 minutos. A base proposta foi mantida com Next.js/TypeScript na interface, FastAPI em Python, PostgreSQL local via Docker Compose e worker Python separado. Publicação e WhatsApp permanecem fora desta etapa.

## Goals / Non-Goals

**Goals:**
- Compartilhar regras de comércio entre interface, Pixel e eventos simulados.
- Manter efeitos de estoque transacionais e idempotentes.
- Preservar catálogo e navegação diante de falhas externas.
- Possibilitar adicionar um adaptador WhatsApp sem reescrever regras comerciais.

**Non-Goals:**
- Um framework de múltiplos agentes ou serviços distribuídos no MVP.
- Hospedar emulação ou arquivos de jogos.
- Tratar uma conversa gerada pelo modelo como registro definitivo de um pedido.

## Decisions

### 1. Aplicação modular com backend comum

Proposta: um backend com módulos de catálogo, comércio, conversação e simulação e uma interface web. Evitar microsserviços reduz a operação de um portfólio; concentrar tudo no navegador exporia credenciais e dificultaria consistência. O backend oferece operações independentes do canal. O chat web adapta mensagens e resultados; WhatsApp será um adaptador posterior.

```text
Catalogo web ------> Backend <------ Chat web
                       |
          +------------+------------+
          |            |            |
       Comercio     Catalogo      Pixel
          |            |            |
       Simulacao     IGDB         Provedor IA
          |            |
          +---- Persistencia

Pagina do jogo ----> Link externo / iframe opcional
```

### 2. Metadados globais, comércio isolado por sessão

Proposta técnica: compartilhar metadados importados, mas criar estoque comercial, carrinho, pedidos e eventos por sessão. Isso impede que uma pessoa esgote a demonstração de outra; a alternativa de estoque global seria mais próxima de uma loja real, mas menos previsível para apresentações.

Modelo lógico:
- Game: identidade IGDB e metadados.
- Platform: uma das seis plataformas, com identificador IGDB resolvido pela API.
- Offer: combinação única de jogo/plataforma e valores fictícios base.
- DemoLink: oferta, provedor, URL externa e URL de incorporação opcional verificada.
- DemoSession / Customer: sessão opaca e persona fictícia gerada pelo sistema.
- SaleStock: quantidade por sessão/oferta.
- RentalCopy: exemplar por sessão/oferta e estado disponível ou alugado.
- Cart / CartItem: versão, modalidade, quantidade e prazo quando aplicável.
- Order / Rental: valores congelados, estado e vínculo ao exemplar.
- SimulationBatch / Event: identidade idempotente, resultado e sessão.
- ImportRun: execução, contagens, estado e erro sanitizado.

A sessão chega ao backend por mecanismo autenticado próprio, não por um identificador escolhido pelo modelo. Pedidos e exemplares de outras sessões não podem ser consultados ou alterados. A persistência relacional é recomendada para transações; SQLite atende uma demonstração com uma única instância e disco persistente, enquanto PostgreSQL atende implantação com múltiplas instâncias. A escolha depende do ambiente de hospedagem.

### 3. Importação IGDB desacoplada das conversas

Usar integração no servidor para autenticar, renovar token quando necessário e importar lotes limitados. Resolver as plataformas pelo IGDB, sem adivinhar seus IDs. Selecionar variedade de gêneros e registrar a combinação jogo/plataforma para eliminar duplicações. Falhas ou respostas parciais não apagam dados existentes.

Importações atualizam apenas metadados. Preços, estoque e condições são criados por configuração fictícia própria; novas ofertas ficam elegíveis para próximas sessões. Sessões existentes preservam seus estoques e pedidos. Uma importação não baixa ROMs ou executáveis.

Uma execução periódica externa chama o mesmo comando usado para a carga inicial. Usar identidade por execução, trava contra sobreposição, limite de requisições e retentativas com espera limitada. Isso é preferível a consultar o IGDB a cada mensagem ou manter um temporizador apenas em memória. A documentação consultada informa quatro requisições por segundo e restrições de CORS: https://api-docs.igdb.com/.

### 4. Comércio transacional e resumo versionado

O catálogo e Pixel chamam as mesmas operações: consultar ofertas, editar carrinho, preparar resumo, confirmar pedido e consultar pedidos. Preços e totais são calculados no servidor em centavos. O carrinho mistura modalidades e identifica plataforma e exemplar/quantidade.

Adicionar um item não reserva estoque. Preparar checkout produz um resumo com versão e condições. Confirmação explícita aponta para esse resumo; alterações exigem outro. Na transação final, revalidar preços, estoque e versão e aplicar pagamento simulado, criação do pedido e movimentação de estoque de modo atômico. Uma chave idempotente evita duplicações por repetição de mensagens ou cliques.

Devoluções liberam apenas o exemplar associado a um aluguel aberto e são idempotentes. Eventos automáticos usam as mesmas operações comerciais, mas têm autor interno de simulação e não se passam por consentimento do visitante.

### 5. Pixel orientado a ferramentas

Um único agente interpreta preferências e utiliza operações de catálogo e comércio com parâmetros validados pelo servidor. A implementação utiliza OpenAI Responses API e o modelo indicado por `PIXEL_OPENAI_MODEL_SNAPSHOT`, validado na conta local.

O modelo não calcula disponibilidade definitiva, não altera estoque diretamente e não obtém segredos. Conteúdo de catálogo e mensagens são dados, não instruções capazes de substituir regras. Identificadores retornados pelas ferramentas devem ser validados novamente em mutações. Confirmação usa o estado do checkout, com suporte a intenção explícita no chat e botão equivalente na interface.

Manter contexto conversacional limitado, prazo de resposta e limites por sessão. Quando IA falhar, catálogo e carrinho continuam disponíveis. A interface atualiza recomendações e carrinho a partir do estado efetivo do backend, não apenas do texto gerado.

### 6. Demonstrações externas selecionadas

Começar com links associados manualmente por oferta; avaliar incorporação para um pequeno conjunto sem assumir cobertura das seis plataformas. URLs devem pertencer a provedores aprovados e não ser HTML arbitrário vindo do chat.

Quando habilitado, carregar o iframe somente após ação do visitante e manter um link externo alternativo. Não tratar embed como direito de distribuição ou como produto comprado. A página consultada oferece código de incorporação, mas compatibilidade no RetroVault ainda precisa ser testada: https://www.retrogames.cc/arcade-games/changes.html.

### 7. Simulação reproduzível com lotes limitados

Proposta: semente pseudoaleatória por sessão, lotes limitados e registro de cada evento. Importação adiciona jogos; demanda gera pedidos e devoluções, sem transformar todos os títulos em estoque infinito. Ambos têm agendas independentes.

O botão “Avançar simulação” executa um lote na sessão atual. A agenda processa apenas sessões ativas com identidade única por intervalo/sessão. Usar uma trava por sessão impede sobreposição manual/automática e confirmação comercial deve permanecer segura sob concorrência. Limitar execução manual por sessão e expirar sessões inativas controla armazenamento e uso.

## Risks / Trade-offs

- [Tokens inválidos ou limites IGDB] → Validar credenciais na implementação, renovar autenticação, importar lotes e servir dados locais.
- [IA inventa disponibilidade ou ação concluída] → Ferramentas validadas e estado comercial como fonte de verdade; testar recusas e falhas.
- [Pedidos e eventos concorrem pelo estoque] → Transações, idempotência e atualização condicional de exemplares.
- [Demonstração externa indisponível] → Links opcionais, teste por plataforma e alternativa fora do iframe.
- [Abuso de uma demonstração pública] → Limites por sessão, expiração e orçamento de chamadas IA.
- [Agendas não executam na hospedagem] → Escolher scheduler compatível com a implantação e verificar execução observável.
- [Credenciais versionadas acidentalmente] → Ignorar `.env` e criar exemplo sem valores reais na etapa de implementação.

## Migration Plan

Aplicação nova, sem dados existentes a migrar. A stack local e a persistência estão definidas abaixo; hospedagem será escolhida na publicação. Na implementação: inicializar aplicação e esquema, configurar segredos do servidor, importar amostra, verificar comércio, conectar Pixel e habilitar agendas após validar execução manual. Publicação é etapa posterior, não autorizada pela criação destes artefatos.

Rollback inicial: desabilitar agendas e integração IA, manter navegação ao catálogo importado e reverter a versão da aplicação. Mudanças de esquema devem ter migrações versionadas; eventos e pedidos não podem ser reaplicados durante recuperação.

## Configuração da implementação

- Python 3.12 com FastAPI; Next.js/TypeScript na interface; PostgreSQL 17 local com volume persistente em Docker Compose.
- Worker Python independente da API executa agendas persistidas com trava PostgreSQL e idempotência por intervalo. Compatível com execução local; hospedagem será escolhida na etapa de publicação.
- OpenAI com o modelo indicado por `PIXEL_OPENAI_MODEL_SNAPSHOT`; o modelo configurado será validado antes de uso, sem substituição automática.
- Amostra de cinco jogos por plataforma; expansão de um título por plataforma a cada 24 horas.
- Demanda a cada 1.800 segundos (30 minutos), até três eventos por sessão/lote e botão manual.
- Defaults fictícios configuráveis: venda R$ 99,90, aluguel R$ 14,90 por sete dias, três unidades de venda e dois exemplares de locação. Retirada fictícia na loja.
- Sessão expira após 24 horas de inatividade; limite inicial de 30 mensagens por hora.

## Verificação e decisões restantes

As evidências estão em `docs/verification.md`. O teste do iframe não confirmou o jogo iniciado; links externos de Chrono Trigger e Super Metroid para SNES permanecem habilitados, com incorporação desabilitada por padrão. Demanda e importação foram verificadas com identities persistidas por janela e banco vazio.

A implantação pública será escolhida posteriormente. Os parâmetros são configuráveis; nenhuma infraestrutura externa foi provisionada. WhatsApp permanece uma mudança posterior.
