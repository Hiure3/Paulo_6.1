#!/usr/bin/env node
// Baixa cada script/estilo de CDN usado nos HTMLs, calcula o hash SHA-384 e grava o atributo integrity="..." na tag.
// Se alguém trocar o arquivo no CDN (ou o CDN for invadido), o navegador RECUSA carregar. Rode UMA vez, com internet:
//     node tools/aplicar-sri.mjs index.html comanda_cliente.html
// Para só conferir se os links ainda respondem e se os hashes continuam iguais:  node tools/aplicar-sri.mjs --check index.html comanda_cliente.html
import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const args = process.argv.slice(2);
const check = args.includes('--check');
const files = args.filter(a => !a.startsWith('--'));
if (!files.length) { console.error('Uso: node tools/aplicar-sri.mjs [--check] index.html comanda_cliente.html'); process.exit(2); }
const allowLocal = process.env.SRI_ALLOW_LOCALHOST === '1';   // só para o autoteste
const cache = new Map();
async function sri(url) {
  if (cache.has(url)) return cache.get(url);
  const r = await fetch(url, { redirect: 'follow' });
  if (!r.ok) throw new Error(`HTTP ${r.status} em ${url}`);
  const hash = 'sha384-' + createHash('sha384').update(Buffer.from(await r.arrayBuffer())).digest('base64');
  cache.set(url, hash); return hash;
}
let problems = 0, changed = 0;
for (const f of files) {
  let html = readFileSync(f, 'utf8');
  const re = /<(script|link)\b[^>]*?(?:src|href)="(https:\/\/[^"]+|http:\/\/localhost[^"]*)"[^>]*>/g;
  const tags = [...html.matchAll(re)];
  for (const m of tags) {
    const tag = m[0], url = m[2];
    if (url.startsWith('http://localhost') && !allowLocal) continue;
    if (/rel="(preconnect|dns-prefetch)"/.test(tag)) continue;
    try {
      const hash = await sri(url);
      const cur = (tag.match(/integrity="([^"]+)"/) || [])[1];
      if (check) {
        if (!cur) { console.log('SEM integrity :', url); problems++; }
        else if (cur !== hash) { console.log('HASH DIFERENTE (conteúdo mudou!):', url); problems++; }
        else console.log('OK            :', url);
        continue;
      }
      let nt = tag.replace(/\s+integrity="[^"]*"/, '');
      if (!/crossorigin=/.test(nt)) nt = nt.replace(/\s*\/?>$/, ' crossorigin="anonymous">');
      nt = nt.replace(/>$/, ` integrity="${hash}">`).replace(/\s+>/, '>');
      if (nt !== tag) { html = html.replace(tag, nt); changed++; }
      console.log('integrity gravado:', url);
    } catch (e) { console.log('FALHA        :', url, '->', e.message); problems++; }
  }
  if (!check) writeFileSync(f, html);
}
console.log(check ? `Conferência terminada: ${problems} problema(s).` : `Pronto: ${changed} tag(s) atualizada(s), ${problems} problema(s).`);
process.exit(problems ? 1 : 0);
