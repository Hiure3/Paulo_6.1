// Testa as regras ANTIGAS (v6) e NOVAS (v7) com ataques e usos legítimos.
const fs = require('fs'), path = require('path');
const { write, canRead } = require('./rules_engine');
const OLD = JSON.parse(fs.readFileSync(process.env.OLD_RULES || path.join(__dirname, 'v6-original/firebase-rules.json'), 'utf8'));
const NEW = JSON.parse(fs.readFileSync(process.env.NEW_RULES || path.join(__dirname, '../firebase-rules.json'), 'utf8'));

const SID1 = 'saaaaaaaaaaaaaaaaaaaaaaaa', SID2 = 'sbbbbbbbbbbbbbbbbbbbbbbbb';
const A = (uid) => ({ uid });
const G = A('G1'), C = A('C1'), K = A('K1'), X = A('X1'), U1 = A('U1'), U2 = A('U2'), U3 = A('U3');
const db = {
  staff: { G1: { name: 'Ger', role: 'Gerente', active: true }, C1: { name: 'Cai', role: 'Caixa', active: true }, K1: { name: 'Coz', role: 'Cozinheiro', active: true }, X1: { name: 'Off', role: 'Caixa', active: false } },
  mesa_sid: { mesa_1: SID1, mesa_2: SID2 },
  sessoes: { [SID1]: { mesa: 1, status: 'ocupada' }, [SID2]: { mesa: 2, status: 'ocupada' } },
  mesa_publica: { mesa_1: { number: 1, status: 'ocupada', sessionId: SID1 }, mesa_2: { number: 2, status: 'ocupada', sessionId: SID2 } },
  acessos: { [SID1]: { U1: true }, [SID2]: { U2: true } },
  historico: { h1: { id: 1, total: 10 } },
  staff_presence: { ping: 1, agent: 'Ana' },
  encomendas: { '-Nowner0000000000000': { uid: 'U2', client: 'Outro', status: 'Recebida', totalValue: 10, sessionId: SID2 } },
  contadores: { encomenda: 7 },
  backups: { 1: { app: 'smartcomanda', localStorage: { smartcomanda_tables_v8: '[]' } } },
  avaliacoes_sessao: { [SID1]: { id: 1, service: 5, food: 5, ts: 1 } },
};
const PUSH = '-Nabcdefghijklmnopqrs';
const goodChat = { sender: 'cliente', text: 'oi', timestamp: 1, time: '10:00', clientName: 'Ana', table: 1 };
const goodEnc = { id: 1, orderNumber: 8, orderCode: 'PEDIDO:08', client: 'Ana', sessionId: SID1, uid: 'U1', mesa: 1, whatsapp: '11999999999', whatsappDigits: '11999999999', date: '2026-11-01', time: '08:00', sector: 'Padaria', status: 'Recebida', itemsList: [{ id: 'p101', name: 'Pão', qty: 2, price: 18.9 }], itemsDescription: '2x Pão', totalValue: 37.8, createdAt: '28/10/2026 10:00' };
const goodFb = { id: 5, receivedAt: 5, sid: SID1, table: 1, client: 'Ana', service: 5, food: 4, total: 10, items: [{ id: 1, name: 'x', qty: 1, price: 1, status: 'Pronto' }], comment: 'ok', time: '10:00' };
const goodFin = { mesa: 1, sid: SID1, client: 'Ana', total: 10, ts: Date.now(), source: 'celular' };

let pass = 0, fail = 0;
function W(rules, upd, auth, d) { return write(rules, d || db, upd, auth).ok; }
function t(name, fn, expectNew, expectOld) {
  const n = fn(NEW), o = fn(OLD);
  const okNew = n === expectNew, okOld = expectOld === undefined || o === expectOld;
  const tag = (okNew && okOld) ? 'OK  ' : 'FALHA';
  if (okNew && okOld) pass++; else fail++;
  const old = expectOld === undefined ? '' : `  [v6: ${o ? 'PERMITIA' : 'negava'}${expectOld === true ? ' <- falha confirmada' : ''}]`;
  console.log(`${tag} ${name}  -> v7: ${n ? 'permite' : 'nega'}${old}`);
}

console.log('--- USOS LEGÍTIMOS (v7 tem que permitir) ---');
t('cliente entra na comanda (acessos/sid/uid=true)', r => W(r, { [`acessos/${SID1}/U3`]: true }, U3), true);
t('cliente lê a própria mesa publicada', r => canRead(r, db, 'mesa_publica/mesa_1', U1), true);
t('cliente envia mensagem no chat', r => W(r, { [`chats/mesa_1/${PUSH}`]: goodChat }, U1), true);
t('cliente envia sinal de vida (clientPing)', r => W(r, { 'chat_meta/mesa_1/clientPing': 123 }, U1), true);
t('cliente envia leitura/digitação (PATCH 2 campos)', r => W(r, { 'chat_meta/mesa_1/clientReadUpTo': 5, 'chat_meta/mesa_1/clientTyping': 6 }, U1), true);
t('cliente pede para finalizar a comanda', r => W(r, { 'finalizar_pedidos/mesa_1': goodFin }, U1), true);
t('cliente cria encomenda válida', r => W(r, { [`encomendas/${PUSH}`]: goodEnc }, U1), true);
t('cliente incrementa contador (+1)', r => W(r, { 'contadores/encomenda': 8 }, U1), true);
t('cliente lê só a própria encomenda', r => canRead(r, { ...db, encomendas: { [PUSH]: goodEnc } }, `encomendas/${PUSH}`, U1), true);
t('cliente lê só o "ping" da presença', r => canRead(r, db, 'staff_presence/ping', U3), true);
t('cliente avalia (feedbacks/fbs_<sid>)', r => W(r, { [`feedbacks/fbs_${SID1}`]: goodFb }, U1, { ...db, avaliacoes_sessao: {} }), true);
t('cliente grava marcador de avaliada (primeira vez)', r => W(r, { [`avaliacoes_sessao/${SID1}`]: { id: 5, service: 5, food: 4, ts: 9 } }, U1, { ...db, avaliacoes_sessao: {} }), true);
t('caixa grava mesas', r => W(r, { tables: [{ number: 1 }] }, C), true);
t('caixa responde no chat como atendente', r => W(r, { [`chats/mesa_1/${PUSH}`]: { sender: 'atendente', agent: 'Cai', text: 'Já vou', timestamp: 2, time: '10:01', clientName: 'Ana', table: 1 } }, C), true);
t('caixa atualiza encomenda (PATCH de status/itens)', r => W(r, { '-Nowner0000000000000/status': 'Em produção', '-Nowner0000000000000/updatedBy': 'Cai' }.constructor === Object ? { 'encomendas/-Nowner0000000000000/status': 'Em produção', 'encomendas/-Nowner0000000000000/updatedBy': 'Cai' } : {}, C), true);
t('cozinheiro cria registro de histórico', r => W(r, { 'historico/h2': { id: 2, total: 5 } }, K), true);
t('gerente apaga histórico', r => W(r, { 'historico/h1': null }, G), true);
t('gerente cadastra colaborador', r => W(r, { 'staff/NEW1': { name: 'Novo', email: 'n@x.com', role: 'Garçom', allowedTabs: ['saloon'], active: true, mustChangePassword: true, createdAt: 1, createdBy: 'Ger' } }, G), true);
t('gerente lê backups', r => canRead(r, db, 'backups', G), true);
t('colaborador troca a própria senha (mustChangePassword=false)', r => W(r, { 'staff/C1/mustChangePassword': false }, C, { ...db, staff: { ...db.staff, C1: { ...db.staff.C1, mustChangePassword: true } } }), true);
t('restauração: gerente grava avaliação fb_<id> antiga', r => W(r, { 'feedbacks/fb_77': { id: 77, service: 4, food: 5, comment: 'ok' } }, G), true);

console.log('\n--- FLUXOS REAIS DA LOJA (v7 tem que permitir) ---');
const caixaOpen = { ...db, mesa_publica: {}, mesa_sid: {}, sessoes: {}, acessos: {} };
t('loja publica comandas em lote (PATCH na raiz, 3 caminhos + remoção)', r => W(r, { 'mesa_publica/mesa_3': { number: 3, status: 'ocupada', whatsapp: '119', items: [] }, 'mesa_sid/mesa_3': 'sdddddddddddddddddddddddd', 'sessoes/sdddddddddddddddddddddddd/mesa': 3, 'sessoes/sdddddddddddddddddddddddd/status': 'ocupada', 'mesa_publica/mesa_1': null, 'mesa_sid/mesa_1': null }, C), true);
t('loja encerra sessão antiga (status/fim)', r => W(r, { [`sessoes/${SID1}/status`]: 'encerrada', [`sessoes/${SID1}/fim`]: 99 }, C), true);
t('loja zera chat e meta da mesa ao finalizar', r => W(r, { 'chats/mesa_1': null, 'chat_meta/mesa_1': null }, C, { ...db, chats: { mesa_1: { [PUSH]: goodChat } }, chat_meta: { mesa_1: { clientPing: 1 } } }), true);
t('loja arquiva a conversa em chats_arquivo', r => W(r, { 'chats_arquivo/mesa_1_123': { mesa: 1, cliente: 'Ana', encerradoEm: 'x', mensagens: { a: goodChat } } }, C), true);
t('loja marca leitura e digitação (chat_meta staff)', r => W(r, { 'chat_meta/mesa_1/staffReadUpTo': 5, 'chat_meta/mesa_1/agent': 'Cai', }, C), true);
t('loja envia sinal de presença {ping, agent}', r => W(r, { 'staff_presence/ping': 5, 'staff_presence/agent': 'Cai' }, C), true);
t('loja remove pedido de finalização já tratado', r => W(r, { 'finalizar_pedidos/mesa_1': null }, C, { ...db, finalizar_pedidos: { mesa_1: goodFin } }), true);
t('loja registra exclusão no log de auditoria', r => W(r, { 'exclusoes/1700': { id: 1700, ts: 1700, tipo: 'Cliente (CRM)', descricao: 'x', detalhes: 'y', uid: 'C1', usuario: 'Cai', cargo: 'Caixa' } }, C), true);
t('loja guarda backup na nuvem (snapshot completo)', r => W(r, { 'backups/1700': { app: 'smartcomanda', version: 1, reason: 'auto', localStorage: { smartcomanda_tables_v8: '[]' }, firebase: { feedbacks: [goodFb], encomendas: [goodEnc] } } }, C), true);
t('gerente poda backups antigos', r => W(r, { 'backups/1': null }, G), true);
t('loja grava venda no histórico (com NFC-e)', r => W(r, { 'historico/h9': { id: 9, mesa: 1, cliente: 'Ana', total: 10, itens: [{ name: 'x', qty: 1, price: 10 }], nfce: { status: 'autorizado', danfe: 'https://x' } } }, C), true);
t('gerente restaura encomendas/avaliações antigas (PATCH em lote)', r => W(r, { 'encomendas/enc_8': goodEnc, 'encomendas/enc_9': { ...goodEnc, id: 9 } }, G), true);
t('gerente ajusta o contador após restaurar', r => W(r, { 'contadores/encomenda': 50 }, G), true);
t('gerente remove acesso de colaborador', r => W(r, { 'staff/C1': null }, G), true);
t('loja edita encomenda (PATCH completo de encPersist)', r => W(r, Object.fromEntries(Object.entries({ itemsList: [{ id: 'p101', name: 'Pão', qty: 1, price: 18.9 }, { id: 'c17', name: 'Avulso', qty: 1, price: 3 }], itemsDescription: '1x Pão', totalValue: 21.9, extraValue: 0, status: 'Pronta para retirada', operator: 'Cai', updatedAt: '28/10 10:00', updatedBy: 'Cai' }).map(([k, v]) => ['encomendas/-Nowner0000000000000/' + k, v])), C), true);
t('cliente reabre a página e relê a própria encomenda por chave local', r => canRead(r, { ...db, encomendas: { [PUSH]: goodEnc } }, `encomendas/${PUSH}`, U1), true);

console.log('\n--- ATAQUES (v7 tem que negar; [v6] mostra se a falha era real) ---');
t('A1 anônimo SEM comanda cria avaliações falsas em massa', r => W(r, { [`feedbacks/${PUSH}`]: { id: 1, service: 1, food: 1, comment: 'spam' } }, U3), false, true);
t('A1b avaliação de outra comanda (sid que não é dele)', r => W(r, { [`feedbacks/fbs_${SID2}`]: { ...goodFb, sid: SID2 } }, U1, { ...db, avaliacoes_sessao: {} }), false);
t('A2 cliente apaga o marcador e avalia de novo', r => W(r, { [`avaliacoes_sessao/${SID1}`]: null }, U1), false, true);
t('A2b segunda avaliação na mesma comanda', r => W(r, { [`feedbacks/fbs_${SID1}`]: goodFb }, U1, { ...db, feedbacks: { [`fbs_${SID1}`]: goodFb } }), false);
t('A3 cliente grava chave __proto__ no chat (poluição de protótipo)', r => W(r, { 'chats/mesa_1/__proto__': { sender: 'cliente', text: 'x', timestamp: 1, polluted: 'sim' } }, U1), false, true);
t('A3b caminho profundo __proto__/x', r => W(r, { 'chats/mesa_1/__proto__/sender': 'cliente' }, U1), false, true);
t('A4 mensagem de chat gigante (600 caracteres)', r => W(r, { [`chats/mesa_1/${PUSH}`]: { ...goodChat, text: 'a'.repeat(600) } }, U1), false, true);
t('A4b campo extra no chat', r => W(r, { [`chats/mesa_1/${PUSH}`]: { ...goodChat, lixo: 'x' } }, U1), false, true);
t('A5 encomenda já "Entregue"', r => W(r, { [`encomendas/${PUSH}`]: { ...goodEnc, status: 'Entregue' } }, U1), false, true);
t('A6 encomenda com valor absurdo', r => W(r, { [`encomendas/${PUSH}`]: { ...goodEnc, totalValue: 999999 } }, U1), false, true);
t('A6b encomenda com valor negativo', r => W(r, { [`encomendas/${PUSH}`]: { ...goodEnc, totalValue: -50 } }, U1), false, true);
t('A7 anônimo lê toda a presença (nome do atendente)', r => canRead(r, db, 'staff_presence', U3), false, true);
t('A8 chave de encomenda com ? e & (injeção na URL)', r => W(r, { 'encomendas/x?y=1&auth=z': goodEnc }, U1), false, true);
t('A9 finalizar mesa de outra comanda (mesa_2)', r => W(r, { 'finalizar_pedidos/mesa_2': { ...goodFin, mesa: 2, sid: SID2 } }, U1), false);
t('A10 finalizar com sid diferente do atual', r => W(r, { 'finalizar_pedidos/mesa_1': { ...goodFin, sid: 'scccccccccccccccccccccccc' } }, U1), false, true);
t('A11 cozinheiro apaga histórico de vendas', r => W(r, { 'historico/h1': null }, K), false, true);
t('A12 caixa lê backups', r => canRead(r, db, 'backups', C), false);
t('A12b cozinheiro vira Gerente (staff/K1/role)', r => W(r, { 'staff/K1/role': 'Gerente' }, K), false);
t('A12c colaborador reativa a própria senha provisória', r => W(r, { 'staff/C1/mustChangePassword': true }, C), false);
t('A12d gerente cria cargo inventado', r => W(r, { 'staff/NEW2': { name: 'x', role: 'Dono', active: true } }, G), false);
t('A13 cliente se cadastra como colaborador', r => W(r, { 'staff/U1': { name: 'x', role: 'Gerente', active: true } }, U1), false);
t('A14 colaborador desativado grava mesas', r => W(r, { tables: [] }, X), false);
t('A15 cliente muda status da sessão', r => W(r, { [`sessoes/${SID1}/status`]: 'ocupada' }, U1), false);
t('A16 cliente finge ser atendente no chat', r => W(r, { [`chats/mesa_1/${PUSH}`]: { ...goodChat, sender: 'atendente' } }, U1), false);
t('A17 cliente escreve no meta da equipe', r => W(r, { 'chat_meta/mesa_1/staffReadUpTo': 5 }, U1), false);
t('A17b cliente escreve no meta de outra mesa', r => W(r, { 'chat_meta/mesa_2/clientPing': 5 }, U1), false);
t('A18 encomenda ligada à comanda de outro cliente', r => W(r, { [`encomendas/${PUSH}`]: { ...goodEnc, sessionId: SID2 } }, U1), false);
t('A18b encomenda em nome de outro uid', r => W(r, { [`encomendas/${PUSH}`]: { ...goodEnc, uid: 'U2' } }, U1), false);
t('A19 avaliação com nota 9', r => W(r, { [`feedbacks/fbs_${SID1}`]: { ...goodFb, service: 9 } }, U1, { ...db, avaliacoes_sessao: {} }), false);
t('A19b avaliação com comentário gigante', r => W(r, { [`feedbacks/fbs_${SID1}`]: { ...goodFb, comment: 'x'.repeat(700) } }, U1, { ...db, avaliacoes_sessao: {} }), false);
t('A20 cliente lê encomenda de outro cliente', r => canRead(r, db, 'encomendas/-Nowner0000000000000', U1), false);
t('A20b cliente lista todas as encomendas', r => canRead(r, db, 'encomendas', U1), false);
t('A21 contador pulando +5', r => W(r, { 'contadores/encomenda': 12 }, U1), false);
t('A22 cliente lê mesas (lista) e chats de outra mesa', r => canRead(r, db, 'tables', U1) || canRead(r, db, 'chats/mesa_2', U1) || canRead(r, db, 'mesa_publica/mesa_2', U1), false);
t('A23 caminho não previsto (/foo) nem para colaborador', r => W(r, { foo: 1 }, G), false);
t('A24 cliente se auto-concede acesso a sid inválido', r => W(r, { 'acessos/curto/U1': true }, U1), false);
t('A24b cliente se auto-concede acesso a sessão encerrada', r => W(r, { [`acessos/${SID1}/U3`]: true }, U3, { ...db, sessoes: { [SID1]: { mesa: 1, status: 'encerrada' } } }), false);
t('A25 colaborador apaga/edita registro de exclusões', r => W(r, { 'exclusoes/5': null }, C, { ...db, exclusoes: { 5: { id: 5, ts: 5, tipo: 'x', uid: 'C1' } } }), false);
t('A26 backup falso (formato inválido) enviado por colaborador', r => W(r, { 'backups/999': { qualquer: 'coisa' } }, C), false);

console.log(`\nResumo: ${pass} verificações OK, ${fail} com falha`);
process.exit(fail ? 1 : 0);
