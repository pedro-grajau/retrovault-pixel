# Verificação da mudança administrativa

Verificada em 12/10/2026, em schema PostgreSQL descartável, separado da demonstração.

- Suíte backend: 29 testes passaram. Abrange migração com dados anteriores, histórico completo e falhas, autenticação/expiração/logout, bloqueio de acesso de visitantes, indicadores sobre preços congelados, mais de 100 pedidos, recorte de datas em America/Fortaleza, inclusão concorrente e desativação com devolução preservada.
- Fluxo integrado: login → busca/seleção → inclusão → recomendação estruturada → carrinho pela interface → pedido → dashboard → expiração pública. Histórico administrativo e receita permanecem consultáveis após expiração.
- Typecheck e build Next.js passaram. O primeiro build no sandbox falhou ao obter configuração do TypeScript; repetido fora do sandbox, concluiu com sucesso, sem desabilitar verificações.
- Chrome headless: login inválido/válido, navegação, dashboard, abertura de conversa e pedido, confirmação de inclusão, revisão/desativação PSP e logout passaram. Desktop de 1440 px e mobile de 390 px; ausência de overflow da página e capturas inspecionadas. Tabelas extensas têm rolagem horizontal própria.
- Inspeção identificou contraste inadequado herdado do tema público; corrigido com tema claro restrito à área administrativa e campos com cor explícita. Capturas refeitas e inspecionadas após a correção.

## Evidências

- [Dashboard desktop](admin-dashboard-desktop.png) e [mobile](admin-dashboard-mobile.png).
- [Jornada desktop](admin-journey-desktop.png) e [mobile](admin-journey-mobile.png).
- [Catálogo desktop](admin-catalog-desktop.png) e [mobile](admin-catalog-mobile.png).
- [Login desktop](admin-login-desktop.png) e [mobile](admin-login-mobile.png).

## Limites

A classificação PSP foi validada com consulta real ao IGDB e fixtures sanitizadas de Patapon, Crisis Core, Final Fantasy VII e Symphony of the Night. A documentação oficial confirma campos de tipo de jogo e datas por plataforma: [IGDB](https://api-docs.igdb.com/#game).

O teste integrado e a verificação visual usam provedores controlados; não consomem tokens OpenAI nem alteram o catálogo da demonstração. O provedor visual retorna uma amostra fixa de títulos, mesmo quando a busca contém texto; a consulta de produção usa o filtro de busca no IGDB. Os dados e credenciais `qa` exibidos nas imagens são exclusivos do teste descartável. Não são credenciais do aplicativo.

Novas credenciais administrativas precisam ser configuradas pelo operador no `.env`, conforme `operations.md`; não existe senha padrão. Mensagens já descartadas antes da migração não são recuperáveis. A revisão de ofertas antigas de PSP exige confirmação no painel, preservando o histórico. A mudança não foi arquivada e o banco da demonstração não foi migrado durante QA; reiniciar a API aplica as migrações.
