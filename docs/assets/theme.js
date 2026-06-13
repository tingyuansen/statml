/* Dark-mode toggle. The theme is set pre-paint by a tiny inline <head> script;
   this file injects the floating toggle button and persists the choice. */
(function () {
  var KEY = 'stig-theme';
  function cur() { return document.documentElement.getAttribute('data-theme') || 'light'; }
  function icon(t) {
    return t === 'dark'
      ? '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>'
      : '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  }
  var btn = document.createElement('button');
  btn.className = 'theme-toggle';
  btn.setAttribute('aria-label', 'Toggle dark / light mode');
  btn.title = 'Toggle dark / light';
  btn.innerHTML = icon(cur());
  btn.addEventListener('click', function () {
    var next = cur() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
    btn.innerHTML = icon(next);
  });
  function add() { document.body.appendChild(btn); }
  if (document.body) add(); else document.addEventListener('DOMContentLoaded', add);
})();
