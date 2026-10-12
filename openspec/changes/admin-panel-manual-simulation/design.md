# Design

## Context

Ver `proposal.md` para motivação. O projeto usa FastAPI, PostgreSQL e Next.js. `sessions.messages` conserva somente 16 mensagens; pedidos, aluguéis e lotes dependem de sessões com exclusão em cascata. O worker avança demanda e importa catálogo em agendas independentes. Estoque só é criado no início da sessão.

Consulta local confirmou PS1 com identificador 7 e PSP com 38, com cinco títulos iguais entre seis ofertas por console. O filtro da interface usa corretamente o slug. A seleção por popularidade do importador não distingue relançamentos; o banco sozinho não prova a classificação de cada lançamento no IGDB.

Não existem specs principais publicadas. A mudança `retrovault-mvp` contém contratos concluídos, incluindo agendas que esta mudança substitui. Não editar nem arquivar aquele planejamento durante esta captura.

## Goals / Non-Goals

**Goals:** separar acesso administrativo do cookie de visitante; produzir indicadores a partir de fatos persistidos; preservar isolamento por sessão; atribuir eventos verificáveis à jornada sem alegar causalidade comercial.

**Non-Goals:** múltiplos papéis administrativos, recuperação de senha, CRM externo, análise por outro modelo de IA ou reconstrução de mensagens já apagadas.

## Decisions

### 1. Admin independente

Proposta de implementação: um admin configurado no servidor por identificador e hash de senha; sem cadastro público. Usar hash com derivação adequada, verificação segura, limitação de tentativas e sessões opacas persistidas com expiração. Cookie HttpOnly separado, SameSite e Secure conforme ambiente; logout revoga a sessão no banco. Toda rota `/api/admin/*` valida autenticação, e mutações reutilizam proteção de origem. Alternativa de esconder botões não protege dados; provedor externo de identidade acrescentaria dependência desnecessária ao portfólio.

### 2. Histórico durável sem sessão pública permanente

Manter a identidade interna da sessão como registro durável, marcando expiração do acesso público. Limpar carrinho, checkouts não utilizados e recursos temporários de sessões inativas, sem apagar pedidos, aluguéis, conversas e eventos. Adaptar o cleanup para não repetir a limpeza e manter exemplares referenciados por aluguéis. Alternativa de exportar históricos antes de cada DELETE exigiria duplicação e sincronização de modelos.

Criar conversas (uma por sessão no fluxo atual), mensagens individuais e eventos da jornada. Mensagens têm estado recebido/respondido/falhou; guardar a entrada antes de chamar o provedor. O campo atual de mensagens pode continuar como janela de contexto, derivada dos registros completos. Migração copia apenas mensagens remanescentes e marca histórico parcial; não inventa horários originais. Dados já apagados não podem ser recuperados.

### 3. Eventos estruturados e origem explícita

Registrar eventos com ID, conversa, mensagem quando aplicável, sessão, oferta, tipo, origem, resultado e horário. Alterações comerciais efetivas e eventos correspondentes devem compartilhar transação. Tentativas recusadas ficam registradas separadamente após rollback. Usar identidades de operação para impedir eventos duplicados em retries.

Adicionar ferramenta do Pixel para registrar recomendações com IDs de ofertas validados. Resultado de busca não equivale a recomendação: a ferramenta devolve as ofertas e serve de referência à resposta. Não extrair recomendações por comparação livre do texto. Ferramentas do Pixel enviam origem `pixel`; endpoints de visitante usam `interface`; demanda usa `simulation`. Guardar origem da confirmação no pedido e vínculos por item quando possível.

O acompanhamento mostra sequência temporal, não prova que Pixel causou uma compra. Conversas sem recomendação podem chegar a pedido. Para conversão, contar conversas distintas com eventos efetivos por etapa no conjunto de conversas iniciadas no período escolhido; excluir pedidos de demanda e informar essa regra na interface. Eventos posteriores ao período de início podem compor a jornada da conversa.

### 4. Indicadores calculados no servidor

Consultar itens congelados de pedidos, evitando recalcular com preços atuais ou multiplicar totais em joins com aluguéis. Receita total é vendas mais aluguéis; devolução não gera receita nem estorno. Datas de pedidos delimitam indicadores comerciais, datas de início delimitam locações. Períodos usam limites explícitos convertidos para UTC; interface usa America/Fortaleza.

Consultas paginadas de pedidos, locações e conversas; agregações sem o limite de 100 pedidos da API pública. Índices por data, conversa e origem. Autor comercial (`visitor`/`simulation`) é distinto do canal (`pixel`/`interface`/legado). Oferecer ambos como filtros onde aplicáveis. Preferir agregação ao consultar em vez de contadores atualizados em vários caminhos.

### 5. Busca e inclusão administrativas

Tela de catálogo no admin: busca por nome e plataforma, paginação limitada, detalhes e confirmação. Reutilizar cliente IGDB com timeout, limite de chamadas e erros sanitizados. Validar novamente a associação de plataforma no servidor antes de inserir, sem confiar em metadados enviados pelo navegador. Preços e quantidades seguem configuração fictícia atual; buscar não modifica dados.

Uma transação cria ou atualiza metadados e oferta e inicializa estoque somente nas sessões públicas ativas. Coordenar a criação de novas sessões e inclusão de ofertas com trava transacional comum para não perder sessões concorrentes. Restrição única jogo/plataforma e inicialização idempotente impedem duplicação e reposição. Consultas existentes continuam lendo estoque por sessão; sessões futuras recebem a oferta no fluxo normal.

### 6. Revisão PSP sem perda de histórico

Verificar campos e relações de lançamentos disponíveis na integração antes de estabelecer a regra de classificação. Usar evidência de lançamento próprio, port ou relançamento; classificação incerta deve ser exibida para revisão, sem ser tratada automaticamente como título próprio de PSP. Priorizar títulos próprios na seleção, mantendo relançamentos identificados e selecionáveis pelo admin.

Adicionar estado ativo à oferta. Revisão apresenta candidatos e classificação ao admin, que confirma desativação; não excluir automaticamente títulos compartilhados entre consoles. Catálogo, Pixel e novos checkouts ignoram ofertas inativas; item já no carrinho exige atualização do resumo. Pedidos e devoluções históricas permanecem válidos. Incluir amostra representativa de títulos próprios pela seleção administrativa.

### 7. Execução manual e manutenção

Retirar chamadas agendadas de demanda e importação do worker; manter apenas cleanup. Remover campos de intervalo nos contratos, mensagens de execução automática e configurações obsoletas. O refresh da interface só consulta dados, sem gerar demanda. Manter limite manual, idempotência e regras transacionais existentes.

UI pública conserva “Avançar simulação”; “Adicionar jogos” fica no admin e não produz demanda. Remover ou proteger comandos CLI de expansão para não contornar a autorização administrativa; eventual carga inicial é operação de manutenção explicitamente documentada, não rotina periódica.

## Risks / Trade-offs

- [Histórico cresce] → Paginação e índices; não fazer limpeza destrutiva implícita. Retenção longa é escolha inicial para o portfólio.
- [Metadados insuficientes para distinguir PSP] → Mostrar classificação incerta e exigir revisão administrativa; testar com respostas reais sanitizadas e fixtures.
- [Evento sem ação ou ação sem evento] → Gravação transacional, idempotência e testes de falhas.
- [Sessões antigas com contexto truncado] → Marcar legado parcial e excluir inferências de conversão.
- [Oferta nova durante checkout ou sessão nova] → Trava consistente e preservação de estoque e versões existentes.

## Migration Plan

1. Criar migrações aditivas para admin, conversas, mensagens, eventos, origem comercial, expiração/limpeza e ofertas ativas; preservar identidades e referências.
2. Migrar mensagens remanescentes e marcar registros antigos como legado. Verificar contagens e totais antes/depois.
3. Configurar hash administrativo fora do Git e ativar gravação de eventos e consultas protegidas.
4. Atualizar frontend e worker em conjunto, retirando agendas; verificar ausência de avanços automáticos.
5. Revisar PSP pelo fluxo administrativo, sem apagar ofertas históricas.

Rollback: parar worker, desabilitar rotas novas e restaurar versão compatível com migrações aditivas. Não restaurar cleanup destrutivo nem agendas do worker antigo; não desfazer migrações apagando histórico ou reaplicar lotes.
