(function () {
  function normalize(input) {
    try {
      if (typeof Request !== 'undefined' && input instanceof Request) {
        const nu = normalize(input.url); return new Request(nu, input);
      }
      if (typeof input !== 'string') return input;
      let s = input.trim();
      if (s.startsWith('//')) s = location.protocol + s;
      s = s.replace(/^http:\/\/(www\.)?rsacrack\.com/i, 'https://rsacrack.com');
      const m = s.match(/^https?:\/\/(www\.)?rsacrack\.com(\/.*)$/i);
      if (m) s = m[2] || '/';
      if (!s.startsWith('/')) s = '/' + s;
      return s;
    } catch (_) { return input; }
  }
  const _fetch = window.fetch;
  window.fetch = function(input, init){ return _fetch(normalize(input), init); };
})();
