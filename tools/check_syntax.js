// Extrai cada <script> inline dos HTMLs e confere se o JavaScript é válido (sem executar).
const fs = require('fs'), vm = require('vm');
let bad = 0;
for (const f of process.argv.slice(2)) {
  const html = fs.readFileSync(f, 'utf8');
  const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;
  let m, i = 0;
  while ((m = re.exec(html))) {
    i++;
    try { new vm.Script(m[1], { filename: f + '#script' + i }); }
    catch (e) { bad++; console.log('ERRO em', f, 'script', i, '->', e.message); }
  }
  console.log(f, ':', i, 'blocos <script> inline verificados');
}
process.exit(bad ? 1 : 0);
