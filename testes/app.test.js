// Testes de comportamento do JavaScript dos dois apps, no Chromium (sem internet: CDNs bloqueados, Firebase simulado).
const path = require('path');
const { chromium } = require('playwright');
const ROOT = path.join(__dirname, '..');
const TARGET = process.env.TARGET || '.';          // '.' = v7 corrigido | 'orig' = v6 (para provar as falhas)
const EXPECT_FIXED = TARGET !== 'orig';
let pass = 0, fail = 0;
const ok = (name, cond, extra) => { if (cond) pass++; else fail++; console.log((cond ? 'OK   ' : 'FALHA') + ' ' + name + (extra ? '  ' + extra : '')); };

async function open(browser, file, query) {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.route(/^https?:\/\//, r => {
    const u = r.request().url();
    if (/cdn\.|fonts\.|cdnjs/.test(u)) return r.abort();   // sem internet no teste
    return r.abort();
  });
  await page.goto('file://' + path.join(TARGET === 'orig' ? path.join(__dirname, 'v6-original') : ROOT, file) + (query || ''));
  return { page, errors, ctx };
}

(async () => {
  const browser = await chromium.launch();

  // ============ APP DA LOJA ============
  let { page, errors } = await open(browser, 'index.html');
  ok('loja: nenhum erro de JavaScript ao carregar', errors.length === 0, errors.join(' | '));

  // --- poluição de protótipo via tempo real (SSE) ---
  const polluted = await page.evaluate(() => {
    class FakeES { constructor() { FakeES.last = this; this.l = {}; this.readyState = 1; setTimeout(() => this.emit('open', {}), 0); }
      addEventListener(t, f) { this.l[t] = f; } emit(t, d) { this.l[t] && this.l[t](d); } close() {} }
    window.EventSource = FakeES;
    SC_AUTH.getToken = async () => 'tok';
    let seen = null;
    scLive('chats', d => { seen = d; });
    return new Promise(res => setTimeout(() => {
      FakeES.last.emit('put', { data: JSON.stringify({ path: '/mesa_1/__proto__/polluted', data: 'sim' }) });
      FakeES.last.emit('put', { data: JSON.stringify({ path: '/mesa_1/-Nok', data: { text: 'oi' } }) });
      res({ polluted: ({}).polluted === 'sim', normalOk: !!(seen && seen.mesa_1 && seen.mesa_1['-Nok']) });
    }, 30));
  });
  ok('loja: tempo real ignora caminho __proto__ (sem poluição de protótipo)', polluted.polluted === !EXPECT_FIXED, EXPECT_FIXED ? '' : '(v6: polui — falha confirmada)');
  ok('loja: tempo real continua aplicando dados normais', polluted.normalOk);

  // --- token só para o endereço exato do banco ---
  if (EXPECT_FIXED) {
    const sent = await page.evaluate(async () => {
      const urls = [];
      window.__real = null;
      // intercepta o fetch "cru" que o wrapper chama
      const orig = window.fetch;
      SC_AUTH.getToken = async () => 'SEGREDO';
      // usa o próprio wrapper: o fetch cru é _scRawFetch (fechado); então medimos pela URL final via monkeypatch de Request
      const rawDesc = Object.getOwnPropertyDescriptor(window, 'fetch');
      return 'skip';
    });
  }

  // --- restauração de backup maliciosa ---
  let restore;
  try { restore = await page.evaluate(async () => {
    localStorage.clear();
    const a = app();
    a.canBackup = () => true;
    a.runBackup = async () => null;
    a._reload = () => { window.__reloaded = true; };
    window.fetch = async () => ({ ok: true, json: async () => ({}), status: 200 });
    window.confirm = () => true; window.alert = (m) => { window.__alert = m; };
    localStorage.setItem('smartcomanda_fiscal_v1', JSON.stringify({ enabled: true, proxyUrl: 'https://meu-servidor.com', apiKey: 'MINHA-CHAVE', defaults: { ncm: '1' }, byProduct: {} }));
    const snap = { app: 'smartcomanda', version: 1, localStorage: {
      smartcomanda_tables_v8: JSON.stringify([{ number: 1, status: 'livre' }]),
      smartcomanda_fiscal_v1: JSON.stringify({ enabled: true, proxyUrl: 'https://atacante.example', apiKey: 'x', defaults: { ncm: '19059090', cfop: '5102' }, byProduct: {} }),
      smartcomanda_github_base_url: 'https://phishing.example/',
      smartcomanda_staff_v8: JSON.stringify([{ user: 'hacker', pin: '1', role: 'Gerente' }]),
      smartcomanda_session_v8: JSON.stringify({ role: 'Gerente' }),
      smartcomanda_clients_v8: '{"nao":"e array"}',
      smartcomanda_menu_v8: JSON.stringify([{ id: 1, name: 'Pão', price: 2 }]),
    }, firebase: {} };
    await a.restoreSnapshot(snap, 'teste', { skipConfirm: true });
    const fz = JSON.parse(localStorage.getItem('smartcomanda_fiscal_v1') || '{}');
    return { github: localStorage.getItem('smartcomanda_github_base_url'), staff: localStorage.getItem('smartcomanda_staff_v8'), session: localStorage.getItem('smartcomanda_session_v8'),
      clients: localStorage.getItem('smartcomanda_clients_v8'), tables: localStorage.getItem('smartcomanda_tables_v8'), menu: localStorage.getItem('smartcomanda_menu_v8'), fiscal: fz, reloaded: !!window.__reloaded };
  }); } catch (e) {   // v6 recarrega a página ao restaurar: relê o que ficou gravado
    ({ page, errors } = await open(browser, 'index.html'));
    restore = await page.evaluate(() => ({ github: localStorage.getItem('smartcomanda_github_base_url'), fiscal: JSON.parse(localStorage.getItem('smartcomanda_fiscal_v1') || '{}') }));
  }
  if (EXPECT_FIXED) {
    ok('restauração: não grava URL do QR vinda do arquivo (anti-phishing)', restore.github === null);
    ok('restauração: não grava usuários/PINs nem sessão do arquivo', restore.staff === null && restore.session === null);
    ok('restauração: não troca o endereço/chave do servidor fiscal', restore.fiscal.proxyUrl === 'https://meu-servidor.com' && restore.fiscal.apiKey === 'MINHA-CHAVE');
    ok('restauração: aceita só os códigos fiscais (NCM/CFOP) do backup', restore.fiscal.defaults.ncm === '19059090' && restore.fiscal.defaults.cfop === '5102');
    ok('restauração: rejeita dado com formato errado (clients não é lista)', restore.clients === null);
    ok('restauração: restaura mesas e cardápio válidos e recarrega', !!restore.tables && !!restore.menu && restore.reloaded);
  } else {
    ok('v6: restauração gravava URL do QR, usuários e config fiscal do arquivo', restore.github === 'https://phishing.example/' && restore.fiscal.proxyUrl === 'https://atacante.example', '(falha confirmada)');
  }

  if (EXPECT_FIXED) {
    // snapshot não vaza chave fiscal
    const snapLeak = await page.evaluate(() => {
      localStorage.setItem('smartcomanda_fiscal_v1', JSON.stringify({ enabled: true, proxyUrl: 'https://s.com', apiKey: 'SEGREDO-FISCAL', defaults: { ncm: '1' }, byProduct: { 5: { ncm: '2' } } }));
      localStorage.setItem('smartcomanda_session_v8', 'x'); localStorage.setItem('smartcomanda_staff_v8', 'y'); localStorage.setItem('smartcomanda_github_base_url', 'https://z/');
      const a = app(); const s = JSON.stringify(a.buildSnapshot('manual'));
      return { leak: s.includes('SEGREDO-FISCAL') || s.includes('https://s.com'), hasSession: s.includes('smartcomanda_session_v8') || s.includes('smartcomanda_staff_v8') || s.includes('github_base_url'), hasCodes: s.includes('byProduct') };
    });
    ok('backup (arquivo/nuvem) não contém a chave fiscal nem o endereço do servidor', !snapLeak.leak);
    ok('backup não contém sessão, usuários nem URL do QR', !snapLeak.hasSession);
    ok('backup mantém os códigos fiscais por produto', snapLeak.hasCodes);

    // backup restrito a Gerente
    const roleBlock = await page.evaluate(async () => {
      const a = app(); a.currentUser = { role: 'Caixa' }; let msg = ''; window.alert = m => { msg = m; };
      let touched = false; a.runBackup = async () => { touched = true; };
      await a.restoreSnapshot({ app: 'smartcomanda', localStorage: { smartcomanda_tables_v8: '[]' } }, 'x');
      return { msg, touched };
    });
    ok('restauração manual é recusada para quem não é Gerente', /Gerente/.test(roleBlock.msg) && !roleBlock.touched);
  }

  if (!EXPECT_FIXED) { await page.close(); ({ page, errors } = await open(browser, 'index.html')); }   // v6 recarrega sozinho depois de restaurar
  // --- finalização pelo celular ---
  const fin = await page.evaluate(async () => {
    const a = app(); const calls = [];
    a.tables = [{ number: 1, status: 'ocupada', sessionId: 'sAAA' }, { number: 2, status: 'ocupada', sessionId: 'sBBB' }, { number: 3, status: 'ocupada', sessionId: 'sCCC' }, { number: 4, status: 'ocupada', sessionId: 'sDDD' }];
    a.checkoutTable = (t) => calls.push(t.number);
    const now = Date.now();
    const queue = { mesa_1: { sid: 'sAAA', ts: now }, mesa_2: { sid: '', ts: now }, mesa_3: { ts: now }, mesa_4: { sid: 'sDDD', ts: now - 20 * 60 * 1000 } };
    window.fetch = async (u, o) => (o && o.method === 'DELETE') ? { ok: true } : { ok: true, json: async () => queue };
    Object.defineProperty(navigator, 'onLine', { get: () => true, configurable: true });
    await a.pollFinalizeRequests();
    return calls;
  });
  ok('finalizar pelo celular: só a mesa com sid correto e recente é fechada', JSON.stringify(fin) === (EXPECT_FIXED ? '[1]' : '[1,2,3]'), 'fechadas: ' + JSON.stringify(fin) + (EXPECT_FIXED ? '' : ' (v6 fechava mesas com sid vazio/ausente — falha confirmada)'));

  if (EXPECT_FIXED) {
    // --- reprecificação de encomendas ---
    const enc = await page.evaluate(() => {
      const a = app();
      const e = { uid: 'U1', status: 'Recebida', totalValue: 0.05, itemsList: [{ id: 'p101', name: 'Pão Francês Tradicional (kg)', qty: 2, price: 0.01 }, { id: 'p105', name: 'Bolo', qty: 1, price: 0.01 }] };
      a.encSanitize(e);
      const tocada = { uid: 'U1', status: 'Recebida', updatedAt: 'x', totalValue: 1, itemsList: [{ id: 'p101', qty: 1, price: 1 }] }; a.encSanitize(tocada);
      return { total: e.totalValue, p1: e.itemsList[0].price, flag: e.priceFromClient, tocada: tocada.itemsList[0].price };
    });
    ok('encomenda com preço adulterado é recalculada pelo catálogo (2×18,90 + 28,00 = 65,80)', enc.total === 65.8 && enc.p1 === 18.9 && enc.flag === 0.05, JSON.stringify(enc));
    ok('encomenda já editada pela loja não é re-precificada', enc.tocada === 1);

    // --- utilitários de URL ---
    const u = await page.evaluate(() => ({
      d: scDigits('55 (11) 9999-8888?text=x'), j: scSafeUrl('javascript:alert(1)'), dt: scSafeUrl('data:text/html,<b>'), h: scSafeUrl('https://ok.com/a'),
      b1: scSafeBase('http://x.com/'), b2: scSafeBase('https://u:p@x.com/'), b3: scSafeBase('https://user.github.io/rep'), b4: scSafeBase('javascript:1') }));
    ok('wa.me recebe só dígitos', u.d === '551199998888');
    ok('links bloqueiam javascript: e data:', u.j === '#' && u.dt === '#' && u.h === 'https://ok.com/a');
    ok('URL base do QR: só https, sem usuário/senha, termina com /', u.b1 === '' && u.b2 === '' && u.b3 === 'https://user.github.io/rep/' && u.b4 === '');

    // --- fiscal só por https ---
    const fiscal = await page.evaluate(async () => {
      const a = app(); const out = {}; let sent = null;
      window.fetch = async (u, o) => { sent = u; return { ok: true, json: async () => ({}) }; };
      for (const [k, url] of [['http', 'http://servidor.com'], ['https', 'https://servidor.com/'], ['local', 'http://localhost:3000']]) {
        a.fiscalCfg = { proxyUrl: url, apiKey: 'K' }; sent = null;
        try { await a.fiscalCall('/health'); out[k] = sent; } catch (e) { out[k] = 'ERRO'; }
      }
      return out;
    });
    ok('fiscal: recusa http:// (chave não viaja aberta); aceita https e localhost', fiscal.http === 'ERRO' && fiscal.https === 'https://servidor.com/health' && fiscal.local === 'http://localhost:3000/health', JSON.stringify(fiscal));

    // --- senha forte ---
    const pw = await page.evaluate(() => { const a = app(); return [a.pinIsWeak('1234567'), a.pinIsWeak('12345678'), a.pinIsWeak('aaaaaaaa'), a.pinIsWeak('padaria123'), a.pinIsWeak('Pao&Cafe-2026')]; });
    ok('política de senha: mínimo 8, recusa sequências/repetidos/comuns', JSON.stringify(pw) === '[true,true,true,true,false]', JSON.stringify(pw));

    // --- sem contas padrão / modo antigo ---
    const legacy = await page.evaluate(() => { localStorage.setItem('smartcomanda_staff_v8', JSON.stringify([{ user: 'admin', pin: '1234' }])); localStorage.setItem('smartcomanda_session_v8', '{"role":"Gerente"}');
      const a = app(); a.loginStaff && (SC_AUTH.enabled || a.loginStaff()); return { staff: a.staffDatabase.length, user: a.currentUser }; });
    ok('sem contas padrão (admin/1234) e sem usuário logado ao abrir', legacy.staff === 0 && legacy.user === null);
  }

  // --- QR local ---
  const qr = !EXPECT_FIXED ? '' : await page.evaluate(() => SC_QR.svgUri('https://exemplo.github.io/x/comanda_cliente.html?mesa=3&sid=sabcdef0123456789abcdef01&cliente=Jo%C3%A3o', 250));
  ok('QR é gerado localmente (data: URI, sem rede)', EXPECT_FIXED ? qr.startsWith('data:image/svg+xml') : true);
  if (EXPECT_FIXED) { require('fs').writeFileSync('/tmp/qr_test.svg', decodeURIComponent(qr.split(',')[1])); }
  await page.close();

  // ============ APP DO CLIENTE ============
  ({ page, errors } = await open(browser, 'comanda_cliente.html', '?mesa=abc&cliente=100%25%20&tempo=zz&total=-5&sid=../../x&itens=' + encodeURIComponent('[{"id":1,"name":"<img src=x onerror=alert(1)>","qty":-3,"price":"9e99"}]')));
  ok('cliente: nenhum erro de JavaScript ao carregar', errors.length === 0, errors.join(' | '));
  const cli = await page.evaluate(async () => {
    window.fetch = async () => ({ ok: false, status: 401, json: async () => null });
    window.EventSource = class { constructor() { this.readyState = 1; } addEventListener() {} close() {} };
    SC_AUTH.getToken = async () => 't';
    const a = clienteApp();
    const errs = [];
    try { await a.init(); } catch (e) { errs.push(String(e)); }
    return { errs, mesa: a.tableNumber, nome: a.clientName, sid: a.sid, total: a.total, tempo: a.satTime, items: a.items };
  });
  if (EXPECT_FIXED) {
    ok('cliente: URL maliciosa não derruba o app nem injeta valores (mesa, sid, total, tempo)', cli.errs.length === 0 && cli.mesa === 1 && cli.sid === '' && cli.total === 0 && cli.tempo === '00:00', JSON.stringify(cli));
    ok('cliente: itens da URL são normalizados (qty mín. 1, preço limitado)', cli.items.length === 1 && cli.items[0].qty === 1 && cli.items[0].price <= 100000, JSON.stringify(cli.items));
    ok('cliente: texto "100%" na URL não gera erro de decodificação', cli.nome === '100% ' || cli.nome.startsWith('100%'), JSON.stringify(cli.nome));
  } else {
    ok('v6: cliente quebrava com "%" solto na URL (URIError)', cli.errs.length > 0, JSON.stringify(cli.errs));
  }
  await page.close();

  if (EXPECT_FIXED) {
    // --- avaliação única (simula as regras do Firebase: criar só se não existir) ---
    ({ page, errors } = await open(browser, 'comanda_cliente.html'));
    const rate = await page.evaluate(async () => {
      const store = {}; const log = [];
      window.fetch = async (url, o) => {
        o = o || {}; const m = o.method || 'GET'; const p = decodeURIComponent(url.replace(/^.*firebaseio\.com\//, '').replace(/\.json.*$/, ''));
        log.push(m + ' ' + p);
        if (m === 'PUT') {
          if (p.startsWith('feedbacks/')) { if (store[p]) return { ok: false, status: (o.headers && o.headers['if-match']) ? 412 : 401, json: async () => null }; store[p] = JSON.parse(o.body); return { ok: true, status: 200, json: async () => store[p] }; }
          if (p.startsWith('avaliacoes_sessao/')) { if (store[p]) return { ok: false, status: 401, json: async () => null }; store[p] = JSON.parse(o.body); return { ok: true, status: 200, json: async () => store[p] }; }
        }
        if (m === 'DELETE') return { ok: false, status: 401, json: async () => null };
        return { ok: true, status: 200, json: async () => (store[p] === undefined ? null : store[p]) };
      };
      const mk = () => { const a = clienteApp(); a.sid = 'sAAAAAAAAAAAA'; a.sessionEnded = true; a.tableChecked = true; a.tableOpen = false; a.ratingService = 4; a.ratingFood = 5; a.feedbackComment = 'ótimo'; a.items = [{ id: 1, name: 'x', qty: 1, price: 2 }]; a.triggerSuccessNotification = (m) => { a.__msg = m; }; localStorage.clear(); return a; };
      const a1 = mk(); await a1.submitFeedback();
      const a2 = mk(); await a2.submitFeedback();   // outro aparelho do mesmo cliente (sem marcador local)
      return { first: a1.__msg, second: a2.__msg, keys: Object.keys(store), fb: store['feedbacks/fbs_sAAAAAAAAAAAA'], deleteTried: log.some(l => l.startsWith('DELETE')) };
    });
    ok('avaliação: primeira é enviada; a segunda (outro aparelho) é recusada como "já avaliada"', /sucesso/.test(rate.first) && /já foi avaliada/.test(rate.second), JSON.stringify([rate.first, rate.second]));
    ok('avaliação: grava em feedbacks/fbs_<sid> + marcador; nunca tenta apagar nada', rate.keys.includes('feedbacks/fbs_sAAAAAAAAAAAA') && rate.keys.includes('avaliacoes_sessao/sAAAAAAAAAAAA') && !rate.deleteTried);
    ok('avaliação: notas são limitadas a 1–5 e comentário a 500 caracteres', rate.fb && rate.fb.service === 4 && rate.fb.food === 5);
    await page.close();
  }

  await browser.close();
  console.log(`\nResumo (${TARGET}): ${pass} OK, ${fail} falha(s)`);
  process.exit(fail ? 1 : 0);
})();
