// Gera o QR da mesa pelo código real da loja, tira "foto" da imagem e decodifica com OpenCV (testes/qr_decode.py).
const path = require('path'), { execFileSync } = require('child_process');
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const page = await (await b.newContext()).newPage();
  await page.route(/^https?:\/\//, r => r.abort());
  await page.goto('file://' + path.join(__dirname, '..', 'index.html'));
  const res = await page.evaluate(() => {
    localStorage.setItem('smartcomanda_github_base_url', 'https://loja.github.io/padaria/');
    const a = app(); a.newSid = () => 'sabcdef0123456789abcdef01'; a.saveStorage = () => {};
    const table = { number: 4, status: 'ocupada', client: 'João', total: 12.5, items: [], satSeconds: 60 };
    a.showTableQrCode(table);
    return { url: a.qrCodeUrl, sidAssigned: table.sessionId };
  });
  await page.setContent('<body style="margin:0;background:#fff"><img id="q" style="width:420px;height:420px"></body>');
  await page.evaluate(u => { document.getElementById('q').src = u; }, res.url);
  await page.waitForTimeout(300);
  await page.locator('#q').screenshot({ path: '/tmp/qr_mesa.png' });
  await b.close();
  const out = execFileSync('python3', [path.join(__dirname, 'qr_decode.py'), '/tmp/qr_mesa.png']).toString().trim();
  console.log('QR decodificado:', out);
  const okUrl = out === 'https://loja.github.io/padaria/comanda_cliente.html?mesa=4&sid=sabcdef0123456789abcdef01';
  console.log((okUrl ? 'OK   ' : 'FALHA') + ' o QR da mesa leva a URL correta COM o sid e foi gerado sem rede');
  process.exit(okUrl ? 0 : 1);
})();
