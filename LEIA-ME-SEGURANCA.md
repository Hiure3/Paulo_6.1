# SmartComanda v7 – Guia de segurança e publicação

Esta versão corrige as falhas encontradas na v6 (lista completa em `RELATORIO-SEGURANCA.md`).
**Ordem importante:** primeiro publique os arquivos HTML novos, **depois** cole as regras. Os HTML novos funcionam com as regras antigas;
as regras novas **não** funcionam com os HTML antigos (a avaliação, a presença e o QR mudaram).

## 1) Firebase (projeto smartcomanda-df58e) – só se ainda não fez na v6
1. **Authentication > Sign-in method**: ative **E-mail/senha** e **Anônimo**.
2. **Authentication > Users**: crie o usuário gerente e copie o **UID**.
3. **Realtime Database > Dados**: crie `staff/<UID>` com `name`, `email`, `role` = `Gerente`, `active` = `true` (booleano).
4. Cargos aceitos pelas regras: `Gerente`, `Garçom`, `Cozinheiro`, `Caixa` (exatamente assim).

## 2) Arquivos
- `SC_API_KEY` já vem preenchida nos dois HTML (se a sua chave for outra, troque nos **dois**). **Sem ela o sistema fica bloqueado** – não existe mais "modo antigo" nem contas `admin/1234`.
- Publique `index.html` e `comanda_cliente.html` juntos (GitHub Pages ou outro https). Peça aos clientes com a página aberta para recarregar.
- **Fixe os hashes dos CDNs (SRI)** – uma vez, no seu computador, com internet:
  `node tools/aplicar-sri.mjs index.html comanda_cliente.html`
  (isso faz o navegador recusar um script de CDN que tenha sido alterado). Depois, de vez em quando: `node tools/aplicar-sri.mjs --check index.html comanda_cliente.html`.
  Se algum link responder 404, troque a versão (Alpine 3.14.9, Chart.js 4.4.7, Tailwind 3.4.17, SheetJS 0.20.3) e rode de novo.

## 3) Teste ANTES de colar as regras
- Entre com o gerente no PC; a tela **não** pode mostrar aviso de bloqueio.
- Abra uma comanda, clique no QR da mesa e escaneie com o celular: o QR agora é gerado no próprio navegador e **leva o `sid`** da comanda.
- No celular: chat, "Finalizar pedido", encomenda e avaliação (a segunda tentativa deve dizer "já avaliada").
- Em CRM & Acessos cadastre um colaborador (e-mail + senha provisória **de 8+ caracteres**); ele deve ser obrigado a trocar a senha.

## 4) Colar as regras
1. **Realtime Database > Regras**: copie e guarde o texto atual.
2. Cole `firebase-rules.json` e **Publicar**.
3. No **Simulador de regras** confira (as regras novas foram testadas só com um avaliador próprio, não com o Firebase real):
   - leitura de `/tables` sem login → **negada**; leitura de `/staff_presence` por usuário anônimo → **negada**, de `/staff_presence/ping` → permitida;
   - escrita em `/feedbacks/qualquer` por anônimo sem comanda → **negada**.
4. Repita o passo 3 dos testes. Se algo parar, restaure as regras antigas e guarde a mensagem de erro.

## 5) Endurecimento no Google/Firebase (recomendado)
- **Google Cloud Console > APIs e serviços > Credenciais > sua chave de API da Web**: restrinja por **referenciador HTTP** (o endereço onde o sistema fica publicado)
  e limite a *Identity Toolkit API* e *Token Service API*. A chave Web não é segredo, mas restringir impede uso por outros sites.
- **Authentication > Configurações**: ative a política de senha (mín. 8) e a proteção contra enumeração de e-mails.
- Use um PC dedicado ao caixa, com bloqueio de tela e disco criptografado (veja "Limitações").

## 6) Emissor fiscal (NFC-e)
A política de segurança (CSP) só deixa o sistema falar com o Firebase. Se você usa o emissor fiscal, abra `index.html`, procure `connect-src` e acrescente
o endereço do seu servidor fiscal (ex.: `https://seu-servidor.onrender.com`) **só no index.html**. O endereço do servidor precisa ser `https://`.
O backup (arquivo e nuvem) **não leva mais** a chave nem o endereço do servidor fiscal, só os códigos NCM/CFOP/CSOSN.

## O que mudou na prática
- Backup/restauração: só o Gerente restaura; o arquivo é conferido (lista fechada de dados; ignora usuários, sessão, URL do QR e config do servidor fiscal).
- Cada comanda tem **uma** avaliação; ela não pode ser apagada nem repetida (mesmo trocando de aparelho).
- O preço da encomenda é recalculado pelo catálogo da loja (o celular do cliente não é confiável).
- Colaborador desativado ou removido perde acesso na hora no banco; só o Gerente apaga histórico de vendas, lê backups e exclusões, e gerencia usuários.

## Limitações a conhecer
- Cliente que troca de aparelho não vê no app os pedidos antigos pelo número (o banco só entrega ao login que criou). Na loja tudo continua visível.
- O QR da mesa é a "chave" da comanda: quem fotografa o QR enquanto a comanda está aberta consegue ver a conta e pedir para finalizar. Cada nova comanda gera outra chave.
- Os cargos controlam o que cada pessoa **vê na tela**; no banco só o que está listado acima é restrito por cargo. Qualquer funcionário ativo ainda lê e grava mesas, encomendas e histórico.
- O contador `PEDIDO:NN` aceita +1 de qualquer login (anônimo inclusive): alguém mal-intencionado pode "queimar" números. Sem backend não há como impedir; **App Check** reduz isso.
- Dados de clientes (nome, WhatsApp, e-mail, aniversário) ficam no navegador do PC da loja (LGPD): use PC dedicado e disco criptografado; "Sair" apaga o login, não os dados.
- O CSP precisa de `unsafe-inline`/`unsafe-eval` (Alpine e Tailwind via CDN): ele limita **para onde** o sistema pode enviar dados e de onde carrega scripts, mas não impede sozinho um XSS. Não há `x-html`/`innerHTML` no código.
- O Tailwind por CDN (modo "play") não é recomendado para produção; o ideal é compilar o CSS. O modo offline (service worker) da v6 nunca funcionou e foi removido.

## Se você usa OUTRO projeto Firebase (ex.: smartcomanda-f5f73)
Os arquivos desta versão vêm apontando para `smartcomanda-df58e` (o mesmo do zip v6 enviado). Para usar outro projeto, nos **dois** HTML troque:
1. `SC_DB` (endereço do banco, `https://SEU-PROJETO-default-rtdb....firebaseio.com`) e `SC_API_KEY` (chave Web do projeto novo);
2. o mesmo endereço do banco dentro de `connect-src` na política de segurança (`<meta http-equiv="Content-Security-Policy" ...>`, no começo do arquivo). **Se esquecer este passo, o navegador bloqueia a conexão e o sistema não carrega dados.**
3. No projeto novo: ative E-mail/senha e Anônimo, crie o gerente em `staff/<UID>` e cole `firebase-rules.json` (passos 1 e 4 deste guia).
