# Tasks

## 1. Histórico e migração

- [x] 1.1 Criar migrações aditivas para conversas, mensagens, eventos, origem de pedidos, ofertas ativas e marcação de sessões expiradas/limpas; verificar aplicação em schema vazio e banco com pedidos e aluguéis existentes sem perda de referências.
- [x] 1.2 Migrar mensagens remanescentes e marcar histórico e origem como legado; testar que não são inventados horários, mensagens ou recomendações.
- [x] 1.3 Substituir exclusão em cascata de sessões por expiração de acesso e limpeza temporária; testar histórico preservado, rejeição pública da sessão expirada e ausência de limpeza repetida.
- [x] 1.4 Documentar preservação de dados e rollback compatível em docs de operações; conferir que o procedimento não reativa cleanup destrutivo.

## 2. Acesso administrativo

- [x] 2.1 Implementar configuração de identificador/hash e sessões administrativas opacas com cookie separado; testar login válido, inválido, expiração, logout e limitação de tentativas.
- [x] 2.2 Proteger todas as rotas administrativas e mutações por autenticação e origem; testar chamadas sem login, cookie de visitante e requisições de origem não autorizada.
- [x] 2.3 Criar tela de login e estrutura `/admin`; verificar navegação, estados de erro e redirecionamento após expiração sem afetar sessão pública.
- [x] 2.4 Documentar configuração segura e login local sem valores reais; verificar que exemplos e logs não expõem credenciais.

## 3. Jornada do Pixel

- [x] 3.1 Persistir entrada, resposta e falhas do chat independentemente da janela de contexto; testar conversa com mais de 16 mensagens e falha do provedor.
- [x] 3.2 Criar registro estruturado de recomendações com ofertas validadas e integrá-lo às ferramentas do Pixel; testar que resultados de busca não recomendados não contam como recomendações.
- [x] 3.3 Instrumentar carrinho, checkout e confirmação com origem e vínculos de jornada em transações idempotentes; testar interação mista, retry, rollback e demanda excluída da conversão.
- [x] 3.4 Criar consultas paginadas de conversas, linha do tempo e etapas/conversão; testar recorte por início da conversa, contagem distinta e jornadas que pulam etapas.
- [x] 3.5 Criar telas administrativas de conversas e detalhe da jornada; verificar histórico completo, falhas, legado parcial e links para pedidos.
- [x] 3.6 Documentar definição das etapas e limite da atribuição temporal; conferir correspondência entre textos da interface e consultas implementadas.

## 4. Dashboard comercial

- [x] 4.1 Implementar agregações de unidades, receita por modalidade e jogos mais vendidos com filtros e índices; testar pedidos mistos, preços históricos e ausência de duplicação por joins.
- [x] 4.2 Implementar consultas de aluguéis abertos, atrasados e devolvidos; testar limites de datas, devolução e receita sem estorno.
- [x] 4.3 Criar dashboard e listas administrativas com paginação e filtros de autor/canal/período/plataforma; verificar valores conhecidos, mais de 100 pedidos e estado vazio.
- [x] 4.4 Documentar cálculo de receita, fuso e períodos comerciais versus coorte de conversa; verificar limites de período em America/Fortaleza nos testes.

## 5. Catálogo administrativo e PSP

- [x] 5.1 Confirmar relações de lançamento disponíveis no IGDB e definir classificação própria/relançamento/incerta; verificar fixtures sanitizadas representativas de PSP e PS1 antes de ativar a regra.
- [x] 5.2 Implementar busca administrativa paginada por título e plataforma e revalidação na inclusão; testar indisponibilidade, incompatibilidade e ausência de mutação durante busca.
- [x] 5.3 Criar inclusão transacional idempotente com estoque para sessões ativas e coordenação com criação de sessão; testar duplicatas concorrentes, novas sessões e preservação de quantidades consumidas.
- [x] 5.4 Criar interface de busca, detalhes, seleção e confirmação no admin; verificar inclusão disponível ao visitante após atualização sem reiniciar sessão.
- [x] 5.5 Implementar revisão e desativação de ofertas PSP sem exclusão histórica; testar rejeição de novo checkout, invalidação de resumo, preservação de pedidos e devolução de aluguel existente.
- [x] 5.6 Documentar operação de busca/inclusão/revisão e proteger ou retirar expansão CLI que contorne autorização; verificar visitante e Pixel impedidos de adicionar títulos.

## 6. Simulação exclusivamente manual

- [x] 6.1 Remover agendas de demanda e expansão do worker, preservando manutenção; testar múltiplos ticks sem novos lotes ou importações.
- [x] 6.2 Ajustar API e configuração para retirar intervalos automáticos e preservar limites e idempotência manuais; executar testes de isolamento, estoque e concorrência do botão.
- [x] 6.3 Atualizar interface pública com fluxo manual e acesso separado à administração; verificar que refresh não altera demanda e inclusão administrativa não gera pedidos.
- [x] 6.4 Atualizar README, contratos e operações para execução manual; conferir que nenhum exemplo recomenda agendas removidas.

## 7. Integração

- [x] 7.1 Executar testes backend, typecheck e build frontend; verificar que os contratos públicos existentes de catálogo, comércio e devoluções continuam consistentes.
- [x] 7.2 Validar fluxo completo login → escolher título → recomendação Pixel → carrinho pela interface → pedido → dashboard → expiração; conferir histórico e totais após expiração.
- [x] 7.3 Verificar visualmente desktop e mobile do painel, login, busca e jornada; registrar evidências e limitações encontradas.

## Workflow follow-up

- Antes de arquivar mudanças, reconciliar os contratos de `retrovault-mvp` e desta mudança nos caminhos `game-catalog` e `portfolio-simulation`, sem reintroduzir importação ou demanda periódicas. Esta captura não autoriza editar ou arquivar o MVP.
