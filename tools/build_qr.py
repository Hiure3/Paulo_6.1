# Gera build/qr_inline.js: gerador de QR Code 100% local (sem rede), baseado em
# "QRCode for JavaScript" de Kazuhiko Arase (licença MIT), empacotado em um único bloco.
import os
SRC = '/usr/lib/node_modules/npm/node_modules/qrcode-terminal/vendor/QRCode'
order = ['QRMode','QRErrorCorrectLevel','QRMaskPattern','QRMath','QRPolynomial','QRBitBuffer','QR8bitByte','QRRSBlock','QRUtil','index']
out = []
out.append("""/* QR Code local (sem chamadas de rede).
 * Baseado em "QRCode for JavaScript" - Copyright (c) 2009 Kazuhiko Arase - Licença MIT
 * http://www.opensource.org/licenses/mit-license.php
 * "QR Code" é marca registrada da DENSO WAVE INCORPORATED. */
window.SC_QR = (function () {
  var __mods = {}, __defs = {};
  function __req(name) { name = name.replace('./', ''); if (!__mods[name]) { var m = { exports: {} }; __defs[name](m, m.exports, __req); __mods[name] = m; } return __mods[name].exports; }
""")
for n in order:
    code = open(os.path.join(SRC, n + '.js'), encoding='utf-8').read()
    # remove cabeçalho de licença duplicado do index (mantemos o nosso acima)
    out.append("  __defs[%r] = function (module, exports, require) {\n%s\n  };\n" % (n, code))
out.append("""
  var QRCode = __req('index'), ECL = __req('QRErrorCorrectLevel');
  // Retorna um data: URI SVG (vetorial) com o QR do texto. Só ASCII: o resto é percent-encoded antes.
  function svgUri(text, px) {
    var t = String(text == null ? '' : text).replace(/[^\\x20-\\x7e]/g, function (c) { return encodeURIComponent(c); });
    var qr = new QRCode(-1, ECL.M); qr.addData(t); qr.make();
    var n = qr.getModuleCount(), q = 4, size = n + q * 2, d = [];
    for (var r = 0; r < n; r++) { var run = -1; for (var c = 0; c <= n; c++) {
      var dark = c < n && qr.isDark(r, c);
      if (dark && run < 0) run = c;
      if (!dark && run >= 0) { d.push('M' + (run + q) + ' ' + (r + q) + 'h' + (c - run) + 'v1h-' + (c - run) + 'z'); run = -1; } } }
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + size + ' ' + size + '" width="' + (px || 250) + '" height="' + (px || 250) + '" shape-rendering="crispEdges"><rect width="100%" height="100%" fill="#fff"/><path fill="#000" d="' + d.join('') + '"/></svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }
  return { svgUri: svgUri, _QRCode: QRCode, _ECL: ECL };
})();
""")
open('build/qr_inline.js','w',encoding='utf-8').write(''.join(out))
print(len(''.join(out)), 'bytes')
