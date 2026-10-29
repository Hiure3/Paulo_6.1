# -*- coding: utf-8 -*-
"""Aplica as correções de segurança no index.html (v6 -> v7). Cada troca confere o trecho original."""
import re, sys

SRC = 'orig/index.html'
DST = 'build/index.html'
s = open(SRC, encoding='utf-8').read()
QR = open('build/qr_inline.js', encoding='utf-8').read()


def rep(old, new, n=1, label=''):
    global s
    c = s.count(old)
    if c != n:
        sys.exit('[%s] esperado %d ocorrência(s), achei %d: %r' % (label, n, c, old[:90]))
    s = s.replace(old, new)


def rep_re(pattern, new, label='', flags=re.S, n=1):
    global s
    m = re.findall(pattern, s, flags)
    if len(m) != n:
        sys.exit('[%s] regex esperado %d, achei %d: %r' % (label, n, len(m), pattern[:90]))
    s = re.sub(pattern, lambda _m: new, s, flags=flags)


CSP = ("default-src 'none'; "
       "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://cdn.sheetjs.com; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
       "font-src https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
       "img-src 'self' data:; "
       "connect-src https://smartcomanda-df58e-default-rtdb.firebaseio.com https://identitytoolkit.googleapis.com https://securetoken.googleapis.com; "
       "object-src 'none'; base-uri 'none'; form-action 'none'")

# ---------------------------------------------------------------- 1) <head>: CSP, versões fixas, anti-iframe, QR local
rep('<title>SmartComanda Ultimate 6.0 - Notificações Inteligentes, Indicadores de Tempo & Edição de Clientes</title>',
    '<title>SmartComanda Ultimate 7.0 - Versão Segura</title>', label='title')
rep('<meta charset="UTF-8">',
    '<meta charset="UTF-8">\n'
    '    <!-- SEGURANÇA: política de conteúdo (só carrega scripts/estilos dos hosts abaixo e só conversa com o Firebase). -->\n'
    '    <!-- Se usar o emissor fiscal, acrescente o endereço do seu servidor fiscal em connect-src (veja LEIA-ME-SEGURANCA.md). -->\n'
    '    <meta http-equiv="Content-Security-Policy" content="' + CSP + '">\n'
    '    <meta name="referrer" content="no-referrer">\n'
    '    <script>try { if (window.top !== window.self) { document.documentElement.style.display = "none"; } } catch (e) { document.documentElement.style.display = "none"; }</script>',
    label='csp')
rep('<script src="https://cdn.tailwindcss.com"></script>',
    '<script src="https://cdn.tailwindcss.com/3.4.17" crossorigin="anonymous" referrerpolicy="no-referrer"></script>', label='tailwind')
rep('<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>',
    '<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>', label='alpine')
rep('<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>',
    '<script src="https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>', label='xlsx')
rep('<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>',
    '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>\n'
    '    <!-- QR Code gerado no próprio navegador (nada é enviado a serviços de terceiros) -->\n'
    '    <script>\n' + QR + '\n    </script>', label='chart')
rep('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">',
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer">', label='fa')

# ---------------------------------------------------------------- 2) tela de login: sem "modo antigo"
rep_re(r'<p x-show="!authOn" class="text-\[11px\] text-amber-300[^>]*>Modo antigo:[^<]*</p>',
       '<p x-show="!authOn" class="text-[11px] text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-2 py-1">Sistema bloqueado: a chave de API do Firebase (SC_API_KEY) não está configurada. Veja o LEIA-ME-SEGURANCA.md.</p>',
       label='login-banner')
rep_re(r'<select x-show="!authOn" x-model="loginInputUser".*?</select>\s*', '', label='login-select')
rep('Nova senha (mín. 6 caracteres) *', 'Nova senha (mín. 8 caracteres) *', label='pwd-label')
rep('Por segurança, a senha provisória/padrão precisa ser trocada antes de usar o sistema.',
    'Por segurança, a senha provisória precisa ser trocada antes de usar o sistema.', label='pwd-text')

# ---------------------------------------------------------------- 3) links externos
rep('<a href="https://www.instagram.com/compreagoranovidades/" target="_blank"',
    '<a href="https://www.instagram.com/compreagoranovidades/" target="_blank" rel="noopener noreferrer"', label='insta')
rep(""":href="'https://wa.me/' + String(atdTable.whatsapp).replace(/\\D/g, '')" target="_blank\"""",
    """:href="'https://wa.me/' + scDigits(atdTable.whatsapp)" target="_blank" rel="noopener noreferrer\"""", label='wa1')
rep(""":href="`https://wa.me/${selectedEncomenda?.whatsapp}`" target="_blank\"""",
    """:href="`https://wa.me/${scDigits(selectedEncomenda?.whatsapp)}`" target="_blank" rel="noopener noreferrer\"""", label='wa2')
rep("""`https://wa.me/${selectedEncomenda?.whatsapp}?text=${encodeURIComponent(""",
    """`https://wa.me/${scDigits(selectedEncomenda?.whatsapp)}?text=${encodeURIComponent(""", label='wa3a')
rep("""formatDataPtBr(selectedEncomenda?.date) + '!')}`" target="_blank\"""",
    """formatDataPtBr(selectedEncomenda?.date) + '!')}`" target="_blank" rel="noopener noreferrer\"""", label='wa3b')
rep(""":href="h.nfce ? h.nfce.danfe : '#'" target="_blank" rel="noopener\"""",
    """:href="h.nfce ? scSafeUrl(h.nfce.danfe) : '#'" target="_blank" rel="noopener noreferrer\"""", label='danfe')
rep('<img :src="qrCodeUrl" alt="QR Code da Conta" class="w-40 h-40 object-contain">',
    '<img :src="qrCodeUrl" alt="QR Code da Conta" class="w-48 h-48 object-contain">', label='qr-img')

# ---------------------------------------------------------------- 4) JS: utilitários de segurança + fetch + tempo real
HELPERS = r"""
        // ===== SEGURANÇA: utilitários =====
        function scDigits(v) { return String(v == null ? '' : v).replace(/\D/g, '').slice(0, 20); }          // só dígitos (links wa.me)
        function scSafeUrl(u) {                                                                                // só http(s): bloqueia javascript:, data: etc.
            try { const x = new URL(String(u || ''), 'https://invalido.local/'); return (x.protocol === 'https:' || x.protocol === 'http:') && x.hostname !== 'invalido.local' ? x.href : '#'; } catch (e) { return '#'; }
        }
        function scSafeBase(u) {                                                                               // base do GitHub Pages: só https, termina com "/"
            try { const x = new URL(String(u || '')); if (x.protocol !== 'https:' || x.username || x.password) return ''; return x.origin + (x.pathname.endsWith('/') ? x.pathname : x.pathname + '/'); } catch (e) { return ''; }
        }
        function scBadKey(k) { return k === '__proto__' || k === 'constructor' || k === 'prototype'; }
        function scHasBadKey(v, depth) {
            depth = depth || 0; if (depth > 12) return true;
            if (Array.isArray(v)) return v.some(x => scHasBadKey(x, depth + 1));
            if (v && typeof v === 'object') return Object.keys(v).some(k => scBadKey(k) || scHasBadKey(v[k], depth + 1));
            return false;
        }
        // chaves do localStorage que podem ser restauradas a partir de um backup (lista fechada; nada de sessão, usuários, URL do QR ou config fiscal)
        const SC_RESTORE_KEYS = {
            smartcomanda_tables_v8: 'array', smartcomanda_orders_v8: 'array', smartcomanda_menu_v8: 'array', smartcomanda_feedbacks_v8: 'array',
            smartcomanda_clients_v8: 'array', smartcomanda_history_v8: 'array', smartcomanda_encomendas_v8: 'array',
            smartcomanda_revenue_v8: 'number', smartcomanda_ontime_v8: 'number', smartcomanda_late_v8: 'number'
        };
        const SC_BACKUP_EXTRA_KEYS = ['smartcomanda_exclusoes_v8'];   // entra no backup (arquivo morto), mas nunca é restaurada
        function scCleanSnapshot(ls) {
            const ok = {}, rejected = [];
            Object.keys(ls || {}).forEach(k => {
                const kind = SC_RESTORE_KEYS[k];
                const v = ls[k];
                if (!kind || typeof v !== 'string' || v.length > 8 * 1024 * 1024) { if (k !== 'smartcomanda_fiscal_v1') rejected.push(k); return; }
                try {
                    if (kind === 'number') { if (!Number.isFinite(parseFloat(v))) throw 0; ok[k] = String(parseFloat(v)); return; }
                    const p = JSON.parse(v);
                    if (!Array.isArray(p) || scHasBadKey(p) || p.some(x => !x || typeof x !== 'object' || Array.isArray(x))) throw 0;
                    ok[k] = v;
                } catch (e) { rejected.push(k); }
            });
            return { ok: ok, rejected: rejected };
        }
        // config fiscal no backup: só códigos fiscais (NCM/CFOP/CSOSN...); NUNCA a chave de acesso nem o endereço do servidor
        function scFiscalForBackup(raw) {
            try {
                const c = JSON.parse(raw || 'null'); if (!c || typeof c !== 'object') return null;
                return JSON.stringify({ defaults: c.defaults || {}, byProduct: c.byProduct || {} });
            } catch (e) { return null; }
        }
        function scFiscalFromBackup(raw, cur) {
            try {
                const c = JSON.parse(raw || 'null'); if (!c || typeof c !== 'object' || scHasBadKey(c)) return null;
                const clean = (o, re) => { const r = {}; Object.keys(o || {}).forEach(k => { const v = o[k]; if (typeof v === 'string' && re.test(v)) r[k] = v; }); return r; };
                const defaults = clean(c.defaults, /^[0-9A-Za-z]{0,8}$/);
                const byProduct = {};
                Object.keys(c.byProduct || {}).forEach(id => { if (/^[0-9A-Za-z_-]{1,20}$/.test(id) && c.byProduct[id] && typeof c.byProduct[id] === 'object') byProduct[id] = clean(c.byProduct[id], /^[0-9A-Za-z]{0,8}$/); });
                return Object.assign({}, cur || {}, { defaults: Object.assign({}, (cur && cur.defaults) || {}, defaults), byProduct: byProduct });
            } catch (e) { return null; }
        }
"""
rep("        const _scRawFetch = window.fetch.bind(window);\n        const SC_AUTH = (function () {",
    "        const _scRawFetch = window.fetch.bind(window);\n" + HELPERS + "        const SC_AUTH = (function () {", label='helpers')
# o token só vai para o endereço EXATO do banco (antes: 'prefixo' casava com firebaseio.com.outro-site)
rep("if (!SC_AUTH.enabled || url.indexOf(SC_DB) !== 0 || /[?&]auth=/.test(url)) return _scRawFetch(input, init);",
    "if (!SC_AUTH.enabled || url.indexOf(SC_DB + '/') !== 0 || /[?&]auth=/.test(url)) return _scRawFetch(input, init);", label='fetch-prefix')
# tempo real: nunca aplica caminhos __proto__/constructor/prototype vindos do servidor (poluição de protótipo)
rep("                const parts = String(p || '/').split('/').filter(Boolean);\n                if (!parts.length) { data = (val === undefined ? null : val); return; }",
    "                const parts = String(p || '/').split('/').filter(Boolean);\n                if (parts.some(scBadKey)) return;   // SEGURANÇA: bloqueia poluição de protótipo\n                if (!parts.length) { data = (val === undefined ? null : val); return; }", label='setIn')

# ---------------------------------------------------------------- 5) sem "modo antigo" / sem contas padrão
rep_re(r"                    const savedStaff = localStorage\.getItem\('smartcomanda_staff_v8'\);.*?                    // Login seguro ligado: cargo e permissões vêm do servidor; lista/PINs e sessão locais deixam de existir\n                    if \(SC_AUTH\.enabled\) \{\n.*?this\.restoreFirebaseSession\(\);\n                    \}\n",
       """                    // SEGURANÇA: o navegador nunca guarda lista de usuários/PINs nem sessão local. Remove restos de versões antigas.
                    try { localStorage.removeItem('smartcomanda_staff_v8'); localStorage.removeItem('smartcomanda_session_v8'); } catch (e) {}
                    this.staffDatabase = [];
                    this.currentUser = null;
                    if (SC_AUTH.enabled) {
                        SC_AUTH.onLost(() => { this.currentUser = null; });
                        this.restoreFirebaseSession();
                    }   // sem SC_API_KEY o sistema fica bloqueado (não existe mais "modo antigo")
""", label='legacy-init')
rep_re(r"                    // Migração \(uma única vez\): libera a nova aba .*?smartcomanda_migr_atendimento_v1', '1'\);\n                    \}\n", "", label='migr')

rep_re(r"                    this\.loginError = '';\n                    if\(!this\.loginInputUser \|\| !this\.loginInputPassword\) \{\n                        this\.loginError = 'Por favor, informe o usuário e a senha\.';.*?this\.loginError = 'Usuário ou senha inválidos\. Tente novamente!';\n                    \}\n",
       "                    this.loginError = 'Login seguro não configurado (SC_API_KEY vazia). Veja o LEIA-ME-SEGURANCA.md.';\n", label='loginStaff-legacy')
rep("                    if (!SC_AUTH.enabled) localStorage.setItem('smartcomanda_session_v8', JSON.stringify(staff));   // com login seguro, a sessão fica só no Firebase\n", "", label='finishLogin-session')
rep_re(r"                    const real = this\.staffDatabase\.find\(x => x\.id === st\.id\); if \(!real\) \{ this\.cancelPinChange\(\); return; \}\n.*?this\.finishLogin\(real\);\n",
       "                    this.cancelPinChange();\n", label='confirmPin-legacy')
rep_re(r"                addStaffManual\(\) \{\n                    if \(SC_AUTH\.enabled\) return this\.addStaffFirebase\(\);\n.*?alert\('Colaborador cadastrado com sucesso!'\);\n                \},",
       "                addStaffManual() {\n                    if (SC_AUTH.enabled) return this.addStaffFirebase();\n                    return alert('Login seguro não configurado (SC_API_KEY vazia).');\n                },", label='addStaffManual')
rep_re(r"                    if\(staff\.user === 'admin'\) return alert\('Não é possível excluir o administrador padrão\.'\);\n.*?localStorage\.setItem\('smartcomanda_staff_v8', JSON\.stringify\(this\.staffDatabase\)\);\n                \},",
       "                },", label='deleteStaff-legacy')
rep("                    localStorage.removeItem('smartcomanda_session_v8');\n                },\n                hasAccess",
    "                    try { localStorage.removeItem('smartcomanda_session_v8'); } catch (e) {}\n                },\n                hasAccess", label='logout')

# ---------------------------------------------------------------- 6) política de senha (mín. 8)
rep("                    if (pin.length < 6) return true;", "                    if (pin.length < 8) return true;", label='pinIsWeak')
rep("['123456', '1234567', '12345678', '654321', '012345', '123123', 'abcdef', 'senha123', 'admin123', 'padaria']",
    "['123456', '1234567', '12345678', '123456789', '87654321', '654321', '012345', '123123', 'abcdef', 'senha123', 'senha1234', 'admin123', 'admin1234', 'padaria', 'padaria123', 'smartcomanda', 'password', 'qwerty123']", n=1, label='weak-list')
rep("if (a.length < 6) { this.pinChangeError = 'A nova senha precisa ter pelo menos 6 caracteres.'; return; }",
    "if (a.length < 8) { this.pinChangeError = 'A nova senha precisa ter pelo menos 8 caracteres.'; return; }", label='pwd-min-change')
rep("                    if (pass.length < 6) return alert('A senha provisória precisa ter pelo menos 6 caracteres.');",
    "                    if (pass.length < 8 || this.pinIsWeak(pass)) return alert('A senha provisória precisa ter pelo menos 8 caracteres e não pode ser fácil de adivinhar (123456, repetidos...).');", label='pwd-min-add')
rep("if (/WEAK_PASSWORD/.test(m)) return 'A senha precisa ter pelo menos 6 caracteres.';",
    "if (/WEAK_PASSWORD/.test(m)) return 'Senha fraca: use pelo menos 8 caracteres.';", label='weak-msg')

# ---------------------------------------------------------------- 7) pedidos de finalização do celular: sessão tem que bater
rep("const outraSessao = req && req.sid && t && t.sessionId && req.sid !== t.sessionId;",
    "const outraSessao = !req || !t || !t.sessionId || req.sid !== t.sessionId;   // SEGURANÇA: sid vazio/ausente também é recusado", label='finalize-sid')

# ---------------------------------------------------------------- 8) chaves do Firebase sempre codificadas em URLs
rep("encomendas/${enc.firebaseKey}.json`, { method: 'DELETE' }",
    "encomendas/${encodeURIComponent(enc.firebaseKey)}.json`, { method: 'DELETE' }", label='enc-del')
rep("encomendas/${k}.json`, { method: 'DELETE' }", "encomendas/${encodeURIComponent(k)}.json`, { method: 'DELETE' }", label='enc-del2')
rep("`${SC_DB}/encomendas/${enc.firebaseKey}.json`, { method: 'PATCH'",
    "`${SC_DB}/encomendas/${encodeURIComponent(enc.firebaseKey)}.json`, { method: 'PATCH'", label='enc-patch')
rep("`${SC_DB}/staff/${staff.id}.json`, { method: 'DELETE' }", "`${SC_DB}/staff/${encodeURIComponent(staff.id)}.json`, { method: 'DELETE' }", label='staff-del')

# ---------------------------------------------------------------- 9) preço da encomenda nunca vem do cliente
rep("""                                    list.sort((a,b) => b.id - a.id);
                                    if(list.length > 0) {
                                        if(list.length > this.encomendasDashboard.length) {""",
    """                                    list.sort((a,b) => b.id - a.id);
                                    list.forEach(e => this.encSanitize(e));
                                    if(list.length > 0) {
                                        if(list.length > this.encomendasDashboard.length) {""", label='enc-load')
rep("                encEnsureItems(enc) {",
    """                // SEGURANÇA: o app do cliente é público; o preço do item NUNCA é confiável. Encomenda nova (ainda não mexida pela loja)
                // tem preços e total recalculados pelo catálogo da loja; se divergir, fica marcada em priceFromClient.
                encSanitize(e) {
                    try {
                        if (!e || !e.uid || e.updatedAt || (e.status && e.status !== 'Recebida')) return e;
                        const raw = e.itemsList; if (!raw || typeof raw !== 'object') return e;
                        const arr = Array.isArray(raw) ? raw : Object.values(raw);
                        const cat = {}; this.encCatalog().forEach(c => { cat[String(c.key)] = c; });
                        let changed = false;
                        arr.forEach(it => {
                            if (!it) return;
                            it.qty = Math.min(Math.max(parseInt(it.qty) || 1, 1), 999);
                            const c = cat[String(it.id)];
                            if (c && Number(it.price) !== Number(c.price)) { it.priceFromClient = it.price; it.price = c.price; changed = true; }
                            else if (!c) { it.price = Math.min(Math.max(Number(it.price) || 0, 0), 100000); }
                        });
                        if (changed) {
                            e.priceFromClient = Number(e.totalValue) || 0;
                            e.itemsList = arr;
                            e.totalValue = Math.round(arr.reduce((a, i) => a + i.qty * i.price, 0) * 100) / 100;
                            console.warn('Encomenda com preço divergente do catálogo foi corrigida:', e.orderCode || e.id);
                        }
                    } catch (err) {}
                    return e;
                },
                encEnsureItems(enc) {""", label='encSanitize')

# ---------------------------------------------------------------- 10) QR local (sem enviar dados a terceiros) e com sid
rep("this.qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=` + encodeURIComponent(qrText);",
    "this.qrCodeUrl = SC_QR.svgUri(qrText, 250);   // gerado aqui no navegador", n=2, label='qr-local')
rep("""                    // URL FIXA POR MESA (ex: comanda_cliente.html?mesa=2) para que o QR Code seja estático e atualize em tempo real
                    const qrText = `${baseUrl}?mesa=${table.number}`;""",
    """                    // O QR leva o identificador da comanda (sid): ele é a "chave" que libera só esta comanda ao celular do cliente
                    if (table.status === 'ocupada' && !table.sessionId) { table.sessionId = this.newSid(); this.saveStorage(); }
                    const qrText = `${baseUrl}?mesa=${table.number}&sid=${encodeURIComponent(table.sessionId || '')}`;""", label='qr-sid')
rep("let savedGithubBase = localStorage.getItem('smartcomanda_github_base_url');",
    "let savedGithubBase = scSafeBase(localStorage.getItem('smartcomanda_github_base_url'));", n=2, label='base-url')
rep("""                            if (savedGithubBase) {
                                if (!savedGithubBase.endsWith('/')) savedGithubBase += '/';""",
    """                            savedGithubBase = scSafeBase(savedGithubBase);   // só https
                            if (savedGithubBase) {
                                if (!savedGithubBase.endsWith('/')) savedGithubBase += '/';""", label='base-url-prompt')

# ---------------------------------------------------------------- 11) fiscal
rep("""                    const base = String(this.fiscalCfg.proxyUrl || '').replace(/\\/+$/, '');
                    const r = await fetch(base + path, {
                        method: method || 'GET',
                        headers: { 'Content-Type': 'application/json', 'x-api-key': this.fiscalCfg.apiKey },
                        body: body ? JSON.stringify(body) : undefined
                    });""",
    """                    const base = String(this.fiscalCfg.proxyUrl || '').trim().replace(/\\/+$/, '');
                    // SEGURANÇA: a chave fiscal só viaja por https (http só em localhost, para testes)
                    if (!/^https:\\/\\/[^\\s/]+/i.test(base) && !/^http:\\/\\/(localhost|127\\.0\\.0\\.1)(:\\d+)?(\\/|$)/i.test(base)) throw new Error('O endereço do servidor fiscal precisa começar com https://');
                    let r;
                    try {
                        r = await fetch(base + path, {
                            method: method || 'GET',
                            headers: { 'Content-Type': 'application/json', 'x-api-key': this.fiscalCfg.apiKey },
                            body: body ? JSON.stringify(body) : undefined
                        });
                    } catch (e) { throw new Error('Sem conexão com o servidor fiscal, ou o endereço dele não está liberado em connect-src na política de segurança (CSP) do index.html.'); }""", label='fiscalCall')
rep("danfe: r.danfe || '', qrcode: r.qrcode || '', urlConsulta: r.urlConsulta || ''",
    "danfe: (r.danfe ? scSafeUrl(r.danfe) : ''), qrcode: r.qrcode || '', urlConsulta: (r.urlConsulta ? scSafeUrl(r.urlConsulta) : '')", label='nota-url')
rep("if (nota.danfe) { try { window.open(nota.danfe, '_blank', 'noopener'); } catch (e) {} }",
    "if (nota.danfe && nota.danfe !== '#') { try { window.open(nota.danfe, '_blank', 'noopener,noreferrer'); } catch (e) {} }", label='danfe-open')

# ---------------------------------------------------------------- 12) backup / restauração
rep("""                        if (k && k.indexOf('smartcomanda_') === 0 && k !== 'smartcomanda_session_v8' && !(SC_AUTH.enabled && k === 'smartcomanda_staff_v8') && k.indexOf('smartcomanda_backup_') !== 0) keys.push(k);""",
    """                        if (k && (SC_RESTORE_KEYS[k] || SC_BACKUP_EXTRA_KEYS.indexOf(k) > -1 || k === 'smartcomanda_fiscal_v1')) keys.push(k);   // lista fechada: nada de sessão, usuários ou chaves""", label='bkKeys')
rep("                    this.bkKeys().forEach(k => { ls[k] = localStorage.getItem(k); });",
    """                    this.bkKeys().forEach(k => {
                        if (k === 'smartcomanda_fiscal_v1') { const f = scFiscalForBackup(localStorage.getItem(k)); if (f) ls[k] = f; return; }   // sem chave de acesso nem endereço do servidor
                        ls[k] = localStorage.getItem(k);
                    });""", label='buildSnapshot')
rep("""                    if (!snap || snap.app !== 'smartcomanda' || !snap.localStorage || typeof snap.localStorage !== 'object') {
                        alert('Backup inválido ou de outro sistema.');
                        return;
                    }""",
    """                    if (!snap || snap.app !== 'smartcomanda' || !snap.localStorage || typeof snap.localStorage !== 'object' || Array.isArray(snap.localStorage)) {
                        alert('Backup inválido ou de outro sistema.');
                        return;
                    }
                    if (!opts.skipConfirm && !this.canBackup()) { alert('Só o Gerente pode restaurar backups.'); return; }
                    const clean = scCleanSnapshot(snap.localStorage);
                    if (!Object.keys(clean.ok).length) { alert('Backup inválido: nenhum dado reconhecido.'); return; }
                    if (clean.rejected.length && !opts.skipConfirm && !confirm('Atenção: ' + clean.rejected.length + ' item(ns) do arquivo foram ignorados por segurança (' + clean.rejected.slice(0, 4).join(', ') + '). Continuar a restauração com o restante?')) return;""", label='restore-validate')
rep_re(r"                        Object\.keys\(snap\.localStorage\)\.forEach\(k => \{\n                            if \(k\.indexOf\('smartcomanda_'\) === 0 .*?\n                            \}\n                        \}\);\n                        const tb = snap\.localStorage\['smartcomanda_tables_v8'\];",
       """                        Object.keys(clean.ok).forEach(k => { localStorage.setItem(k, clean.ok[k]); });
                        if (snap.localStorage['smartcomanda_fiscal_v1']) {   // só códigos fiscais; endereço e chave do servidor ficam como estão
                            let cur = null; try { cur = JSON.parse(localStorage.getItem('smartcomanda_fiscal_v1') || 'null'); } catch (e) {}
                            const merged = scFiscalFromBackup(snap.localStorage['smartcomanda_fiscal_v1'], cur);
                            if (merged) localStorage.setItem('smartcomanda_fiscal_v1', JSON.stringify(merged));
                        }
                        const tb = clean.ok['smartcomanda_tables_v8'];""", label='restore-write')
rep("""                            const mx = Math.max(0, ...arrE.map(e => (e && e.orderNumber) || 0));
                            if (mx) {""",
    """                            const mx = Math.min(1000000, Math.max(0, ...arrE.map(e => (e && Number.isFinite(Number(e.orderNumber)) && Number(e.orderNumber)) || 0)));
                            if (mx) {""", label='restore-counter')
rep("                        location.reload();\n                    } catch (e) {\n                        this._restoring = false;",
    "                        this._reload();\n                    } catch (e) {\n                        this._restoring = false;", label='reload')
rep("                async restoreList(path, list, prefix) {\n                    const arr = Array.isArray(list) ? list : (list && typeof list === 'object' ? Object.values(list) : []);",
    "                _reload() { location.reload(); },\n                async restoreList(path, list, prefix) {\n                    const arr = (Array.isArray(list) ? list : (list && typeof list === 'object' ? Object.values(list) : [])).filter(x => x && typeof x === 'object' && !scHasBadKey(x));", label='restoreList-a')
rep("if (it && it.id !== undefined && !have.has(String(it.id))) { const c = Object.assign({}, it); delete c.firebaseKey; patch[prefix + it.id] = c; n++; }",
    "if (it && /^[0-9A-Za-z_-]{1,40}$/.test(String(it.id)) && !have.has(String(it.id))) { const c = Object.assign({}, it); delete c.firebaseKey; patch[prefix + it.id] = c; n++; }", label='restoreList-b')

# ---------------------------------------------------------------- 13) tela fiscal: aviso de https
rep('placeholder="https://seu-servidor.onrender.com"', 'placeholder="https://seu-servidor.onrender.com (somente https)"', label='fiscal-ph')

# ---------------------------------------------------------------- 14) service worker "offline" que nunca funcionou (registro via blob: é recusado pelos navegadores)
rep_re(r"    <!-- REGISTRO DE SERVICE WORKER PARA FUNCIONAMENTO 100% OFFLINE \(PWA\) -->\n    <script>.*?</script>\n", "", label='service-worker')

open(DST, 'w', encoding='utf-8').write(s)
print('index.html ok:', len(s), 'bytes')
