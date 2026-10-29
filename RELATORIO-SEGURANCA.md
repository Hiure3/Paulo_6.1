# Relatório de segurança – SmartComanda v6 → v7

Escopo: `index.html` (loja), `comanda_cliente.html` (celular), `firebase-rules.json`, guia de segurança. Método: leitura completa do código, modelagem do que um
**cliente mal-intencionado** (celular, login anônimo), um **funcionário de cargo baixo** e um **arquivo de backup adulterado** conseguem fazer, e teste de cada falha
(antes e depois). Gravidade: Alta = perda de dados/dinheiro ou controle do PC da loja; Média = fraude ou vazamento com condições; Baixa = endurecimento.

## Falhas encontradas e correções

| # | Gravidade | Falha (v6) | Correção (v7) | Teste |
|---|---|---|---|---|
| 1 | Alta | **Poluição de protótipo pelo tempo real.** O cliente podia gravar a chave `__proto__` no chat; o PC da loja aplicava esse caminho em `Object.prototype` (altera todos os objetos do sistema). | Os dois apps ignoram `__proto__/constructor/prototype`; as regras exigem chave gerada pelo Firebase e campos conhecidos. | app.test (v6 polui, v7 não) + regras A3/A3b |
| 2 | Alta | **Restauração de backup sem validação**: qualquer chave `smartcomanda_*` do arquivo ia para o navegador – inclusive endereço/chave do servidor fiscal (a chave fiscal passa a ser enviada ao atacante) e a URL base do QR (QR de phishing). Qualquer cargo podia restaurar; um backup falso na nuvem era oferecido na abertura. | Lista fechada de dados, formato conferido, `__proto__` rejeitado; fiscal só aceita códigos NCM/CFOP/CSOSN; só o Gerente restaura; regras exigem formato de backup. | app.test (restauração maliciosa) |
| 3 | Alta | **Segredo fiscal em backups** (nuvem e arquivo para download). | Backup grava só códigos fiscais, nunca chave nem endereço do servidor. | app.test |
| 4 | Alta | **QR por serviço de terceiros** (`api.qrserver.com`): a URL com `sid` (a "chave" da comanda), nome, itens e total era enviada a um site externo. O QR da mesa ainda saía **sem `sid`**, quebrando o acesso do cliente. | QR gerado no navegador (biblioteca MIT embutida); o QR da mesa leva o `sid`. | qr.test (decodifica a imagem) + csp_static |
| 5 | Alta | **"Modo antigo" aberto por padrão**: com `SC_API_KEY` vazia valiam as contas `admin/1234`, `garcom`, `cozinha`, `caixa`, com PIN em texto no navegador e sessão guardada. | Removido. Sem a chave o sistema bloqueia. Restos antigos do navegador são apagados na abertura. | csp_static + app.test |
| 6 | Alta | **Regras: avaliações falsas ilimitadas** (qualquer login anônimo, mesmo sem comanda) e **avaliar de novo** (o cliente podia apagar a própria "trava"). | Avaliação em chave fixa `feedbacks/fbs_<sid>`, criada uma vez, só por quem pertence à comanda; marcador só pode ser criado. Notas 1–5 e textos limitados. | regras A1/A2/A19 + app.test (2º aparelho) |
| 7 | Alta | **Regras sem validação**: encomenda já "Entregue", valor absurdo/negativo, mensagens gigantes, campos extras, chaves com `?`/`&`. | Status inicial obrigatório, valor 0–20.000, tamanhos e tipos, chave de 20 caracteres do Firebase. | regras A4–A8, A18 |
| 8 | Média | **Preço da encomenda confiado ao celular** (dava para mandar o pedido com preço 0,01). | A loja recalcula preços e total pelo catálogo de encomendas ainda não editadas; divergência fica marcada (`priceFromClient`). | app.test |
| 9 | Média | **Finalizar pelo celular aceitava `sid` vazio** e as regras não conferiam o `sid` atual da mesa. | Loja exige sessão igual; regras exigem `sid` = sessão atual da mesa. | app.test + regras A10 |
| 10 | Média | **Cargos só na tela**: um cozinheiro podia apagar o histórico de vendas; cadastro de usuário sem validação de cargo. | Apagar histórico só Gerente; `staff` com cargos válidos e campos conhecidos; backups/exclusões como antes. | regras A11–A12d |
| 11 | Média | **Cadeia de fornecimento**: Alpine `@3.x.x` e Chart.js sem versão (qualquer atualização maliciosa roda com o login da loja); sem CSP; SheetJS 0.18.5 com falhas conhecidas (CVE-2023-30533, CVE-2024-22363). | Versões fixas, SheetJS 0.20.3, CSP (hosts de script e destinos de rede fechados), `tools/aplicar-sri.mjs` para travar o hash. | csp_static (bloqueia fetch/script/img/iframe externos) |
| 12 | Média | **Token enviado por "prefixo" de URL** (`…firebaseio.com.outro-site`). | Só vai para `…firebaseio.com/`. | revisão de código |
| 13 | Baixa | Presença expunha o **nome do atendente** a qualquer anônimo. | Só o campo `ping` é público. | regras A7 |
| 14 | Baixa | `wa.me/` com texto do cliente; link do DANFE vindo do servidor (`javascript:`); `target=_blank` sem `rel`; URL base do QR sem checar; fiscal aceitava `http://`. | Só dígitos; só http(s); `rel="noopener noreferrer"`; só https; fiscal só https (ou localhost). | app.test + csp_static |
| 15 | Baixa | Senha mínima de 6 e lista fraca curta. | Mínimo 8 e lista maior. | app.test |
| 16 | Baixa | App do cliente confiava nos parâmetros da URL (`%` solto derrubava o app; valores sem limite). | Tamanho, formato e tipo conferidos. | app.test |
| 17 | Baixa | Service worker "offline" nunca funcionou (o navegador recusa `blob:`) e listava CDNs sem versão. | Removido. | teste manual no Chromium |
| 18 | Baixa | Sem proteção contra abrir o sistema dentro de iframe (clickjacking). | Página se esconde se estiver em iframe. | csp_static |

## Como foi testado (e o que NÃO foi)
- `testes/regras.test.js` – 76 verificações das regras (37 usos legítimos/fluxos reais da loja e 39 ataques), rodando as regras **v6 e v7** num avaliador próprio:
  13 dos ataques passavam na v6; na v7 todos os 39 são negados e nenhum uso legítimo foi bloqueado.
- `testes/app.test.js` – 30 verificações do JavaScript dos dois apps no Chromium com Firebase simulado (rode com `TARGET=orig` para ver as falhas na v6).
- `testes/csp_static.test.js` – 26 verificações (CSP bloqueia destinos externos e libera os CDNs usados; links, versões, ausência de `innerHTML`/`eval`).
- `testes/qr.test.js` – gera o QR da mesa pelo código real e decodifica a imagem com OpenCV.
- **Não testado:** (a) as regras no Firebase real – use o Simulador (guia, passo 4); (b) a interface com Alpine/Tailwind renderizados, porque o ambiente de teste não tinha internet
  para baixar os CDNs: testei a lógica (funções) e conferi as pequenas alterações de HTML, mas faça o roteiro do passo 3 do guia; (c) os hashes SRI e a existência das versões fixadas –
  rode `tools/aplicar-sri.mjs`.

## Riscos que continuam (sem backend não há como eliminar)
1. Qualquer login anônimo pode somar +1 no contador `PEDIDO:NN` (queimar números) e criar contas/sessões em massa → **App Check** e cotas do Firebase.
2. O QR da mesa é a chave da comanda; funcionários ativos têm acesso amplo a mesas/encomendas/histórico (só o que está no guia é restrito por cargo).
3. Dados pessoais de clientes e o login da loja ficam no navegador do PC; a CSP reduz o risco de roubo, não o de acesso físico.
4. A chave de API Web é pública por natureza: restrinja por referenciador no Google Cloud (guia, seção 5).
