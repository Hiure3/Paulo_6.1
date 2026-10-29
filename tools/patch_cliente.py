# -*- coding: utf-8 -*-
"""Aplica as correções de segurança no comanda_cliente.html (v6 -> v7)."""
import re, sys

SRC = 'orig/comanda_cliente.html'
DST = 'build/comanda_cliente.html'
s = open(SRC, encoding='utf-8').read()
QR_NOT_NEEDED = True


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


# o app do cliente só fala com o Firebase (sem scripts de planilha/gráfico)
CSP = ("default-src 'none'; "
       "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
       "font-src https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
       "img-src 'self' data:; "
       "connect-src https://smartcomanda-df58e-default-rtdb.firebaseio.com https://identitytoolkit.googleapis.com https://securetoken.googleapis.com; "
       "object-src 'none'; base-uri 'none'; form-action 'none'")

# ---------------------------------------------------------------- head
rep('<meta charset="UTF-8">',
    '<meta charset="UTF-8">\n'
    '    <!-- SEGURANÇA: política de conteúdo (só carrega scripts/estilos dos hosts abaixo e só conversa com o Firebase). -->\n'
    '    <meta http-equiv="Content-Security-Policy" content="' + CSP + '">\n'
    '    <meta name="referrer" content="no-referrer">\n'
    '    <script>try { if (window.top !== window.self) { document.documentElement.style.display = "none"; } } catch (e) { document.documentElement.style.display = "none"; }</script>',
    label='csp')
rep('<script src="https://cdn.tailwindcss.com"></script>',
    '<script src="https://cdn.tailwindcss.com/3.4.17" crossorigin="anonymous" referrerpolicy="no-referrer"></script>', label='tailwind')
rep('<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>',
    '<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>', label='alpine')
rep('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">',
    '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer">', label='fa')
rep('<a href="https://www.instagram.com/compreagoranovidades/" target="_blank"',
    '<a href="https://www.instagram.com/compreagoranovidades/" target="_blank" rel="noopener noreferrer"', label='insta')

# ---------------------------------------------------------------- limites nos campos (as regras do banco recusam textos maiores)
rep('x-model="newMessage" @input="onChatInput()"', 'x-model="newMessage" maxlength="500" @input="onChatInput()"', label='chat-max')
rep('<input type="text" x-model="feedbackComment" placeholder', '<input type="text" x-model="feedbackComment" maxlength="500" placeholder', label='comment-max')
rep('<input type="text" x-model="encName" placeholder', '<input type="text" x-model="encName" maxlength="80" placeholder', label='encName-max')
rep('<input type="text" x-model="encWhatsapp" placeholder', '<input type="text" x-model="encWhatsapp" maxlength="30" inputmode="tel" placeholder', label='encWa-max')
rep('<input type="text" x-model="encDescription" placeholder', '<input type="text" x-model="encDescription" maxlength="300" placeholder', label='encDesc-max')

# ---------------------------------------------------------------- JS: fetch, tempo real
rep("if (!SC_AUTH.enabled || url.indexOf(SC_DB) !== 0 || /[?&]auth=/.test(url)) return _scRawFetch(input, init);",
    "if (!SC_AUTH.enabled || url.indexOf(SC_DB + '/') !== 0 || /[?&]auth=/.test(url)) return _scRawFetch(input, init);", label='fetch-prefix')
rep("                const parts = String(p || '/').split('/').filter(Boolean);\n                if (!parts.length) { data = (val === undefined ? null : val); return; }",
    "                const parts = String(p || '/').split('/').filter(Boolean);\n"
    "                if (parts.some(k => k === '__proto__' || k === 'constructor' || k === 'prototype')) return;   // SEGURANÇA: bloqueia poluição de protótipo\n"
    "                if (!parts.length) { data = (val === undefined ? null : val); return; }", label='setIn')

# ---------------------------------------------------------------- parâmetros da URL (entrada não confiável)
rep_re(r"                    const urlParams = new URLSearchParams\(window\.location\.search\);\n.*?if\(urlParams\.get\('sid'\)\) \{\n                        this\.urlSid = urlParams\.get\('sid'\);   // sessão \(cliente\) para a qual este link/QR foi gerado\n                        this\.sid = urlParams\.get\('sid'\);\n",
       """                    // SEGURANÇA: tudo que vem da URL é entrada não confiável (tamanho, formato e tipo conferidos)
                    if (!SC_AUTH.enabled) { this.clientName = 'Sistema não configurado'; this.tableChecked = true; return; }   // sem SC_API_KEY o app não funciona (não há "modo antigo")
                    const urlParams = new URLSearchParams(window.location.search);
                    const mesaParam = parseInt(urlParams.get('mesa'), 10);
                    if (Number.isInteger(mesaParam) && mesaParam > 0 && mesaParam < 1000) this.tableNumber = mesaParam;

                    if (urlParams.get('cliente')) {
                        this.clientName = String(urlParams.get('cliente')).slice(0, 80);
                        this.encName = this.clientName;
                    }
                    if (urlParams.get('tempo') && /^\\d{1,3}:\\d{2}$/.test(urlParams.get('tempo'))) this.satTime = urlParams.get('tempo');
                    if (urlParams.get('total')) this.total = Math.min(Math.max(parseFloat(urlParams.get('total')) || 0, 0), 1000000);
                    if (urlParams.get('sid') && /^[A-Za-z0-9_-]{8,64}$/.test(urlParams.get('sid'))) {
                        this.urlSid = urlParams.get('sid');   // sessão (cliente) para a qual este link/QR foi gerado
                        this.sid = urlParams.get('sid');
""", label='url-params')
rep("""                    if(urlParams.get('itens')) {
                        try { const it = JSON.parse(urlParams.get('itens')); if (Array.isArray(it)) this.items = it; } catch(e) {}
                    }""",
    """                    if(urlParams.get('itens') && urlParams.get('itens').length <= 6000) {
                        try {
                            const it = JSON.parse(urlParams.get('itens'));
                            if (Array.isArray(it)) this.items = it.slice(0, 80).filter(x => x && typeof x === 'object').map(x => ({ id: (typeof x.id === 'number' || typeof x.id === 'string') ? String(x.id).slice(0, 40) : undefined, name: String(x.name || '').slice(0, 120), qty: Math.min(Math.max(Number(x.qty) || 1, 1), 999), price: Math.min(Math.max(Number(x.price) || 0, 0), 100000), status: String(x.status || '').slice(0, 30) }));
                        } catch(e) {}
                    }""", label='url-itens')

# presença: só o campo "ping" é público (o nome do atendente fica só para a equipe)
rep("""                    scLive('staff_presence', (data) => {
                        const ping = data && data.ping ? data.ping : 0;""",
    """                    scLive('staff_presence/ping', (data) => {
                        const ping = typeof data === 'number' ? data : 0;""", label='presence')

# ---------------------------------------------------------------- chat: tamanhos
rep("                    const text = (typeof textOverride === 'string' ? textOverride : this.newMessage).trim();\n                    if (!text) return;",
    "                    const text = (typeof textOverride === 'string' ? textOverride : this.newMessage).trim().slice(0, 500);\n                    if (!text) return;", label='chat-text')
rep("clientName: this.clientName || 'Cliente Mesa ' + this.tableNumber,",
    "clientName: String(this.clientName || 'Cliente Mesa ' + this.tableNumber).slice(0, 80),", label='chat-name')

# ---------------------------------------------------------------- finalizar pedido: campos limitados
rep("""                        client: this.clientName || '',
                        total: this.total || 0,
                        ts: Date.now(),
                        source: 'celular'""",
    """                        client: String(this.clientName || '').slice(0, 80),
                        total: Number(this.total) || 0,
                        ts: Date.now(),
                        source: 'celular'""", label='finalize-fields')

# ---------------------------------------------------------------- avaliação única (sem "trava" apagável)
rep_re(r"                // Reserva a avaliação desta comanda no Firebase\..*?                async submitFeedback\(\) \{.*?                        this\.submittingRating = false;\n                    \}\n                \},\n",
       r"""                // A avaliação é gravada UMA vez, em uma chave fixa por comanda (feedbacks/fbs_<sid>). O banco só aceita criar essa chave
                // se ela ainda não existe e se este login pertence à comanda: não dá para avaliar duas vezes nem apagar a avaliação.
                async postFeedbackOnce(sid, fb) {
                    const fbUrl = `${SC_DB}/feedbacks/${encodeURIComponent('fbs_' + sid)}.json`;
                    const lockUrl = `${SC_DB}/avaliacoes_sessao/${encodeURIComponent(sid)}.json`;
                    const r = await fetch(fbUrl, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'if-match': 'null_etag' }, body: JSON.stringify(fb) });
                    if (r.status === 412) return 'exists';
                    if (r.status === 401 || r.status === 403) {          // recusado: ou já existe, ou este login não pertence à comanda
                        const g = await fetch(lockUrl, { cache: 'no-store' });
                        if (g.ok && (await g.json()) !== null) return 'exists';
                        throw new Error('HTTP ' + r.status);
                    }
                    if (!r.ok) throw new Error('HTTP ' + r.status);
                    // marcador de "já avaliada" (só criar; falhar aqui não invalida a avaliação)
                    try { await fetch(lockUrl, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: fb.id, service: fb.service, food: fb.food, ts: Date.now() }) }); } catch (e) {}
                    return 'ok';
                },

                async submitFeedback() {
                    if (!this.canRate || this.submittingRating) return;
                    this.submittingRating = true;
                    const sid = this.ratingSid;
                    const clampStar = (v) => Math.min(5, Math.max(1, Math.round(Number(v) || 5)));
                    const fb = {
                        id: Date.now(),
                        receivedAt: Date.now(),   // data/hora em que o sistema recebeu a avaliação
                        sid: sid,
                        table: this.tableNumber,
                        client: String(this.clientName || 'Cliente').slice(0, 80),
                        service: clampStar(this.ratingService),
                        food: clampStar(this.ratingFood),
                        total: Number(this.total) || 0,
                        items: (this.items || []).slice(0, 80).map(i => ({ id: (i && (typeof i.id === 'number' || typeof i.id === 'string')) ? String(i.id).slice(0, 40) : undefined, name: String((i && i.name) || '').slice(0, 120), qty: Math.min(Math.max(Number(i && i.qty) || 1, 1), 999), price: Math.min(Math.max(Number(i && i.price) || 0, 0), 100000), status: String((i && i.status) || '').slice(0, 30) })),
                        comment: String(this.feedbackComment || 'Sem comentários').slice(0, 500),
                        time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
                    };
                    try {
                        const res = await this.postFeedbackOnce(sid, fb);
                        if (res === 'exists') {
                            this.markRated(sid, null);
                            this.triggerSuccessNotification('Esta comanda já foi avaliada. Obrigado!', 'fa-star');
                            return;
                        }
                        this.markRated(sid, { service: fb.service, food: fb.food });
                        this.feedbackComment = '';
                        this.triggerSuccessNotification('Avaliação enviada com sucesso!');
                    } catch (e) {
                        this.triggerSuccessNotification('Não foi possível enviar. Tente novamente.', 'fa-triangle-exclamation');
                    } finally {
                        this.submittingRating = false;
                    }
                },
""", label='feedback', n=1)

# ---------------------------------------------------------------- encomenda: validações antes de enviar
rep("""                    if(!this.encName || !this.encWhatsapp) {
                        alert('Por favor, informe seu Nome e WhatsApp para a encomenda!');
                        return;
                    }""",
    """                    if(!this.encName || !this.encWhatsapp) {
                        alert('Por favor, informe seu Nome e WhatsApp para a encomenda!');
                        return;
                    }
                    if (String(this.encWhatsapp).replace(/\\D/g, '').length < 8 || String(this.encWhatsapp).replace(/\\D/g, '').length > 15) {
                        alert('Informe um WhatsApp válido (com DDD).');
                        return;
                    }""", label='enc-validate')
rep("""                        client: this.encName,
                        sessionId: this.sid,          // vincula a encomenda ao cliente ativo da mesa""",
    """                        client: String(this.encName).trim().slice(0, 80),
                        sessionId: this.sid,          // vincula a encomenda ao cliente ativo da mesa""", label='enc-client')
rep("""                        whatsapp: this.encWhatsapp,
                        whatsappDigits: String(this.encWhatsapp).replace(/\\D/g, ''),""",
    """                        whatsapp: String(this.encWhatsapp).trim().slice(0, 30),
                        whatsappDigits: String(this.encWhatsapp).replace(/\\D/g, '').slice(0, 20),""", label='enc-wa')
rep("""                        date: this.encDate,
                        time: this.encTime,""",
    """                        date: /^\\d{4}-\\d{2}-\\d{2}$/.test(this.encDate) ? this.encDate : '',
                        time: /^\\d{2}:\\d{2}$/.test(this.encTime) ? this.encTime : '',""", label='enc-date')
rep("const itemsText = selectedItemsList.join(', ') + (this.encDescription ? ` (Obs: ${this.encDescription})` : '');",
    "const itemsText = (selectedItemsList.join(', ') + (this.encDescription ? ` (Obs: ${String(this.encDescription).slice(0, 300)})` : '')).slice(0, 1500);", label='enc-text')

# o nome da chave de armazenamento local só aceita formato conhecido (evita caminho forjado na URL do banco)
rep("""                        try {
                            const r = await fetch(`${SC_DB}/encomendas/${k}.json`, { cache: 'no-store' });""",
    """                        try {
                            if (!/^-[A-Za-z0-9_-]{15,25}$/.test(String(k))) return null;
                            const r = await fetch(`${SC_DB}/encomendas/${encodeURIComponent(k)}.json`, { cache: 'no-store' });""", label='enc-key')

open(DST, 'w', encoding='utf-8').write(s)
print('comanda_cliente.html ok:', len(s), 'bytes')
