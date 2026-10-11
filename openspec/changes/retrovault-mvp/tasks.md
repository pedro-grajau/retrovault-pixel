# Tasks

Esta lista acompanha implementação e verificação. Os contratos estão em `specs/`, as decisões em `design.md` e as evidências em `docs/verification.md`.

## 1. Decisões e base da aplicação

- [x] 1.1 Selecionar stack, banco, hospedagem/scheduler e provedor/modelo de IA e definir amostra, preços, prazos e intervalos configuráveis; verificar que as decisões estão registradas no design e que o ambiente suporta persistência e tarefas periódicas.
- [x] 1.2 Inicializar interface web e backend modular na stack selecionada; verificar inicialização local e build pelos comandos registrados no README.
- [x] 1.3 Configurar segredos apenas no servidor, ignorar `.env` e criar exemplo sanitizado; verificar que `.env` é ignorado pelo Git e que segredos não aparecem no bundle, respostas ou logs de falha.
- [x] 1.4 Criar migrações para catálogo, ofertas, sessões, carrinhos, estoques separados, exemplares, pedidos e eventos; verificar aplicação das migrações em banco vazio e unicidade por jogo/plataforma.

## 2. Catálogo IGDB

- [x] 2.1 Implementar autenticação IGDB no servidor com renovação e erros sanitizados; verificar uma consulta autenticada com as credenciais locais sem imprimir seus valores e testar falha de autenticação.
- [x] 2.2 Resolver as seis plataformas e importar a amostra configurada com metadados e ofertas fictícias; verificar cobertura de cada plataforma, tratamento de campos ausentes e ausência de duplicações na segunda importação.
- [x] 2.3 Implementar expansão periódica em lotes com limite de chamadas, retentativas limitadas e registro de execuções; verificar execução manual e agendada, atualização de metadados sem sobrescrever comércio e preservação do catálogo em falha externa.
- [x] 2.4 Construir navegação, busca, filtros e página do jogo; verificar combinações jogo/plataforma, ausência de resultados, imagens ausentes e uso em tela móvel.
- [x] 2.5 Documentar configuração e operação da importação; verificar que um ambiente novo consegue carregar e repetir a amostra pelos comandos documentados.

## 3. Comércio físico e sessão

- [x] 3.1 Criar sessões com personas fictícias e estoques comerciais isolados; verificar que iniciar demonstração dispensa dados reais e que uma sessão não acessa pedidos ou estoque de outra.
- [x] 3.2 Implementar carrinho compartilhado e preços calculados no servidor com modalidades e plataformas explícitas; verificar inclusão, remoção e atualização de itens sem reserva antecipada de estoque.
- [x] 3.3 Implementar resumo versionado, confirmação explícita e pagamento fictício com pedido transacional idempotente; testar confirmação repetida, resumo desatualizado, pagamento falho e concorrência pela última unidade sem pedido parcial.
- [x] 3.4 Implementar aluguel de exemplares e devolução simulada idempotente; testar indisponibilidade durante aluguel e devolução repetida sem incremento indevido.
- [x] 3.5 Construir carrinho, resumo, confirmação e consulta de pedidos no site; verificar compra e locação pelos botões, com identificação clara da simulação e sem campos de pagamento real.
- [x] 3.6 Documentar estados de pedido, aluguel e sessão e suas operações; verificar exemplos de venda, locação e devolução usando os contratos do backend.

## 4. Pixel no chat web

- [x] 4.1 Integrar o provedor escolhido a operações validadas de consulta, carrinho e checkout vinculadas à sessão; verificar que preços e disponibilidade vêm das ferramentas e que não há acesso direto do modelo ao banco ou a segredos.
- [x] 4.2 Construir chat em português com contexto limitado, estados de resposta e atualização do carrinho a partir do backend; verificar continuidade da conversa e alternância entre catálogo e chat no mesmo carrinho.
- [x] 4.3 Implementar esclarecimento de plataforma/modalidade e confirmação do resumo no chat; testar seleção ambígua, título ausente, orçamento sem resultados e tentativa de concluir sem confirmação.
- [x] 4.4 Adicionar limites de uso e tratamento de indisponibilidade da IA; testar acesso a outra sessão, tentativas de ignorar estoque e falha do provedor mantendo catálogo e carrinho utilizáveis.
- [x] 4.5 Documentar operações do Pixel e fronteira do adaptador de canal; verificar uma conversa completa de recomendação até pedido com estado persistido, sem exigir implementação WhatsApp.

## 5. Demonstrações jogáveis

- [x] 5.1 Cadastrar links de demonstração para uma seleção validada de jogos/plataformas e provedores aprovados; verificar cada destino, não exibir botão para ofertas sem associação e preservar sessão/carrinho ao retornar.
- [x] 5.2 Avaliar o iframe oferecido pelo RetroGames.cc em um título compatível e habilitar incorporação somente se funcionar; verificar carregamento sob ação do visitante, comportamento em tela móvel e link externo alternativo, documentando o resultado mesmo se a opção permanecer desabilitada.
- [x] 5.3 Expor as associações ao Pixel e identificar o serviço externo na interface; verificar que Pixel não inventa URLs e que compra ou aluguel não promete desbloquear acesso digital.

## 6. Demanda fictícia

- [x] 6.1 Implementar lotes limitados de vendas, aluguéis e devoluções pelos serviços comerciais, com semente por sessão e identidade de evento; testar estoque esgotado, eventos repetidos e devoluções elegíveis.
- [x] 6.2 Implementar botão “Avançar simulação”, histórico e agenda para sessões ativas com trava por sessão e expiração; testar concorrência manual/agendada, isolamento entre visitantes e atualização de disponibilidade exibida.
- [x] 6.3 Documentar controles, parâmetros, limites e operação do scheduler; verificar um avanço manual e uma execução periódica pelos procedimentos documentados.

## 7. Verificação integrada do MVP

- [x] 7.1 Executar jornadas completas de compra e locação alternando catálogo e Pixel, com demonstração externa e devolução; verificar o atendimento dos cenários das cinco especificações e registrar evidências.
- [x] 7.2 Verificar degradação sob falhas IGDB, IA e demonstração externa e sob concorrência entre checkout e simulação; confirmar catálogo preservado, estoques consistentes e ausência de vazamento entre sessões.
- [x] 7.3 Revisar experiência móvel e instruções de execução do portfólio em ambiente limpo; verificar distinção entre metadados reais e operações fictícias e que agendas e importação podem ser reproduzidas.

## Workflow follow-up

- Revisar implementação e evidências antes de arquivar.
- Publicar apenas quando solicitado; validar a implantação e as agendas no ambiente escolhido.
- Arquivar com `$openspec-archive-change` após implementação e verificação concluídas.
- Planejar WhatsApp como mudança posterior que reutiliza operações do backend.
