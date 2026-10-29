# Testes (opcional – para quem tem Node.js)
Instale uma vez: `npm i playwright && npx playwright install chromium` e `pip install opencv-python-headless` (só para o teste do QR). Depois, nesta pasta:

    node regras.test.js          # regras v6 x v7 (não precisa de internet nem de navegador)
    node app.test.js             # JavaScript dos apps (Chromium; CDNs são bloqueados de propósito)
    TARGET=orig node app.test.js # mostra as falhas da v6 (para comparar)
    node csp_static.test.js      # política CSP e verificações estáticas
    node qr.test.js              # gera o QR da mesa e decodifica a imagem

`v6-original/` guarda os arquivos da versão anterior só para comparação. **Não publique** essa pasta.
As regras são avaliadas por um interpretador próprio (`rules_engine.js`), que NÃO substitui o Simulador de regras do console do Firebase.
