// Mini avaliador de regras do Firebase Realtime Database (subconjunto usado por este projeto).
// Serve para testar as regras sem acessar um Firebase real. NÃO substitui o Simulador do console (veja LEIA-ME).
String.prototype.matches = function (re) { return re.test(this); };

class Snap {
  constructor(v) { this.v = v === undefined ? null : v; }
  child(p) { let cur = this.v; for (const k of String(p).split('/').filter(Boolean)) { cur = (cur !== null && typeof cur === 'object' && Object.prototype.hasOwnProperty.call(cur, k)) ? cur[k] : null; } return new Snap(cur); }
  val() { return this.v; }
  exists() { return this.v !== null && this.v !== undefined; }
  hasChild(k) { return this.child(k).exists(); }
  hasChildren(a) { if (this.v === null || typeof this.v !== 'object') return false; return a ? a.every(k => this.hasChild(k)) : Object.keys(this.v).length > 0; }
  isString() { return typeof this.v === 'string'; }
  isNumber() { return typeof this.v === 'number'; }
  isBoolean() { return typeof this.v === 'boolean'; }
}
const getAt = (root, path) => path.reduce((c, k) => (c !== null && typeof c === 'object' && Object.prototype.hasOwnProperty.call(c, k)) ? c[k] : null, root);
const clone = (x) => JSON.parse(JSON.stringify(x === undefined ? null : x));
function setAt(root, path, val) {
  const r = clone(root) || {};
  if (!path.length) return clone(val);
  let n = r;
  for (let i = 0; i < path.length - 1; i++) { if (!Object.prototype.hasOwnProperty.call(n, path[i]) || n[path[i]] === null || typeof n[path[i]] !== 'object') Object.defineProperty(n, path[i], { value: {}, enumerable: true, writable: true, configurable: true }); n = n[path[i]]; }
  const lk = path[path.length - 1];
  if (val === null) delete n[lk]; else Object.defineProperty(n, lk, { value: clone(val), enumerable: true, writable: true, configurable: true });   // defineProperty: a chave __proto__ vira propriedade comum (como no Firebase)
  return r;
}
function prune(x) { if (x && typeof x === 'object') { for (const k of Object.keys(x)) { x[k] = prune(x[k]); if (x[k] === null || (typeof x[k] === 'object' && !Object.keys(x[k]).length)) delete x[k]; } } return x; }

function ev(expr, ctx) {
  if (expr === true || expr === false) return expr;
  const names = ['auth', 'root', 'data', 'newData', 'now'].concat(Object.keys(ctx.vars));
  const fn = new Function(...names, 'return (' + expr + ');');
  try { return !!fn(ctx.auth, new Snap(ctx.root), new Snap(ctx.data), new Snap(ctx.newData), Date.now(), ...Object.values(ctx.vars)); } catch (e) { return false; }
}
function ruleChild(node, key) {
  if (!node || typeof node !== 'object') return null;
  if (Object.prototype.hasOwnProperty.call(node, key) && !key.startsWith('.')) return [node[key], null];
  const w = Object.keys(node).find(k => k.startsWith('$'));
  return w ? [node[w], w] : null;
}
function walkRules(rules, path) {   // devolve [{rule, path, vars}] do raiz até o nó mais profundo
  const out = []; let node = rules.rules, vars = {};
  out.push({ rule: node, path: [], vars: { ...vars } });
  for (let i = 0; i < path.length; i++) {
    const rc = ruleChild(node, path[i]); if (!rc) break;
    node = rc[0]; if (rc[1]) vars = { ...vars, [rc[1]]: path[i] };
    out.push({ rule: node, path: path.slice(0, i + 1), vars: { ...vars } });
  }
  return out;
}
function canRead(rules, db, pathStr, auth) {
  const path = pathStr.split('/').filter(Boolean);
  for (const n of walkRules(rules, path)) {
    if (n.rule['.read'] !== undefined && ev(n.rule['.read'], { auth, root: db, data: getAt(db, n.path), newData: getAt(db, n.path), vars: n.vars })) return true;
  }
  return false;
}
function validateTree(rules, oldRoot, newRoot, auth, paths) {   // como o Firebase: valida só o que foi escrito (e os ancestrais), não o banco todo
  function rec(rule, path, vars, onlyChildren) {
    const nv = getAt(newRoot, path);
    if (nv === null) return true;
    if (!onlyChildren && rule['.validate'] !== undefined && !ev(rule['.validate'], { auth, root: oldRoot, data: getAt(oldRoot, path), newData: nv, vars })) return false;
    if (nv !== null && typeof nv === 'object') {
      for (const k of Object.keys(nv)) { const rc = ruleChild(rule, k); if (!rc) continue; if (!rec(rc[0], path.concat(k), rc[1] ? { ...vars, [rc[1]]: k } : vars, false)) return false; }
    }
    return true;
  }
  for (const p of paths) {
    const chain = walkRules(rules, p);
    for (let i = 0; i < chain.length; i++) {
      const n = chain[i], last = i === chain.length - 1 && chain.length === p.length + 1;
      if (last) { if (!rec(n.rule, n.path, n.vars, false)) return false; }
      else { const nv = getAt(newRoot, n.path); if (nv !== null && n.rule['.validate'] !== undefined && !ev(n.rule['.validate'], { auth, root: oldRoot, data: getAt(oldRoot, n.path), newData: nv, vars: n.vars })) return false; }
    }
    // escrita mais funda do que as regras descrevem: não há mais nada a validar abaixo
  }
  return true;
}
// updates: { 'a/b/c': valor|null, ... }  (PUT = 1 entrada; PATCH multi-caminho = várias; tudo ou nada)
function write(rules, db, updates, auth) {
  let newRoot = db;
  for (const [p, v] of Object.entries(updates)) newRoot = setAt(newRoot, p.split('/').filter(Boolean), v === undefined ? null : v);
  newRoot = prune(clone(newRoot)) || {};
  for (const p of Object.keys(updates)) {
    const path = p.split('/').filter(Boolean);
    let ok = false;
    for (const n of walkRules(rules, path)) {
      if (n.rule['.write'] !== undefined && ev(n.rule['.write'], { auth, root: db, data: getAt(db, n.path), newData: getAt(newRoot, n.path), vars: n.vars })) { ok = true; break; }
    }
    if (!ok) return { ok: false, why: 'sem permissão de escrita em /' + p };
  }
  if (!validateTree(rules, db, newRoot, auth, Object.keys(updates).map(p => p.split('/').filter(Boolean)))) return { ok: false, why: 'dados inválidos (.validate)' };
  return { ok: true, db: newRoot };
}
module.exports = { write, canRead, Snap };
