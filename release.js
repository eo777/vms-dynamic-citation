window.SG_RELEASE = {"version":"2026.10.28.11","build":"9e9951f597cc","date":"2026-10-28","docs":null};
// Release stamp and update check, added to the published copy by publish/publish.py (the workspace app has neither).
// GitHub Pages lets a browser reuse a page for up to ten minutes. Every file the page loads carries a hash of its
// contents (?v=...), so a page always gets the files it was released with; to notice a newer release, this script
// asks for version.json, bypassing the cache, and offers a reload.
(function () {
  'use strict';
  var R = window.SG_RELEASE;
  function stamp() {
    var tag = document.getElementById('releaseTag');
    if (!tag) return;
    tag.textContent = ' · v' + R.version;
    tag.title = 'Release ' + R.version + ' of ' + R.date + ', build ' + R.build;
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', stamp); else stamp();

  if (!/^https?:$/.test(location.protocol) || !window.fetch) return;   // a copy opened from disk has no server to ask
  var EVERY = 10 * 60 * 1000, last = 0, offered = false;
  function check() {
    if (offered || Date.now() - last < EVERY) return;
    last = Date.now();
    fetch('version.json?t=' + last, {cache: 'no-store'})
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (v) { if (v && v.build && v.build !== R.build) offer(v); })
      .catch(function () {});
  }
  function offer(v) {
    offered = true;
    var style = document.createElement('style');
    style.textContent = '.release-update{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:1000;display:flex;'
      + 'align-items:center;gap:10px;max-width:calc(100% - 32px);padding:8px 8px 8px 14px;border:1px solid var(--line2,#d3d1ca);'
      + 'border-radius:10px;background:var(--surface,#fcfcfb);color:var(--ink,#0b0b0b);box-shadow:var(--shadow,0 4px 16px rgba(0,0,0,.12));'
      + 'font:13px/1.4 system-ui,sans-serif}'
      + '.release-update button{font:inherit;cursor:pointer;border:1px solid var(--ink,#0b0b0b);border-radius:6px;padding:3px 10px;'
      + 'background:var(--ink,#0b0b0b);color:var(--surface,#fcfcfb)}'
      + '.release-update button.release-close{border-color:transparent;background:transparent;color:var(--muted,#8a8984);padding:3px 6px}';
    document.head.appendChild(style);
    var bar = document.createElement('div');
    bar.className = 'release-update';
    bar.setAttribute('role', 'status');
    var text = document.createElement('span');
    text.textContent = 'Version ' + v.version + ' is available.';
    var reload = document.createElement('button');
    reload.type = 'button'; reload.textContent = 'Reload';
    reload.onclick = function () { location.reload(); };
    var close = document.createElement('button');
    close.type = 'button'; close.className = 'release-close'; close.textContent = '×';
    close.setAttribute('aria-label', 'Dismiss');
    close.onclick = function () { bar.remove(); };
    bar.append(text, reload, close);
    document.body.appendChild(bar);
  }
  window.addEventListener('load', function () { setTimeout(check, 1500); });
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible') check(); });
})();
