/* TradePulse.AI — page behaviour
   Reads the bot's own status endpoint and renders what it says.
   Nothing on this page is hard-coded market data. */
(function () {
  'use strict';

  var STATUS_API = 'https://bot.tradepulseai.co.uk/?format=json';
  var LIVE_SINCE = Date.UTC(2026, 6, 16);      // 2026-07-16, first paper bar
  var REFRESH_MS = 5 * 60 * 1000;

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var nf2 = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var $ = function (id) { return document.getElementById(id); };

  /* ── bot status ─────────────────────────────────────────── */
  var POS = { '1': 'LONG', '0': 'FLAT', '-1': 'SHORT' };

  function relTime(iso) {
    var t = Date.parse(String(iso).replace(' ', 'T'));
    if (isNaN(t)) return '';
    var mins = Math.round((Date.now() - t) / 60000);
    if (mins < 2) return 'just now';
    if (mins < 60) return mins + ' min ago';
    var h = Math.round(mins / 60);
    if (h < 48) return h + 'h ago';
    return Math.round(h / 24) + 'd ago';
  }

  function actionOf(d) {
    if (!d.action) return 'HOLD';
    var to = +d.action.to, from = +d.action.from;
    if (to > from) return 'BUY';
    if (to < from) return 'SELL';
    return 'HOLD';
  }

  function renderState(data) {
    var posN = String(parseInt(data.position, 10) || 0);
    var posEl = $('mPosition');
    if (posEl) {
      posEl.textContent = POS[posN] || '?';
      posEl.setAttribute('data-pos', posN === '1' ? 'long' : posN === '-1' ? 'short' : 'flat');
    }
    if ($('mEquity')) $('mEquity').textContent = '$' + nf2.format(+data.equity || 0);

    var ret = +data.total_return_pct || 0;
    if ($('mReturn')) {
      $('mReturn').textContent = (ret >= 0 ? '+' : '') + ret.toFixed(2) + '%';
      $('mReturn').style.color = ret > 0 ? 'var(--up)' : ret < 0 ? 'var(--down)' : '';
    }
    if ($('mDaysLive')) {
      $('mDaysLive').textContent = String(Math.max(0, Math.floor((Date.now() - LIVE_SINCE) / 86400000)));
    }
    if ($('stateAge')) $('stateAge').textContent = 'updated ' + relTime(data.updated_at);

    if (window.TP && data.trades) window.TP.setTrades(data.trades);
  }

  function renderTape(decisions) {
    var run = $('tapeRun');
    if (!run || !decisions || !decisions.length) return;

    var cells = decisions.slice().reverse().map(function (d) {
      var act = actionOf(d);
      var day = String(d.bar || '').slice(0, 10);
      var px = +d.price;
      return '<span class="tape__cell">' +
        '<span class="tape__date">' + day + '</span>' +
        '<span class="tape__px">' + (isFinite(px) ? nf2.format(px) : '—') + '</span>' +
        '<span class="tape__act" data-a="' + act + '">' + act + '</span>' +
        '</span>';
    }).join('');

    run.innerHTML = cells + cells;   // duplicated: the marquee loops at -50%
  }

  function loadStatus() {
    fetch(STATUS_API, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (data) {
        renderState(data);
        renderTape(data.recent_decisions);
      })
      .catch(function () {
        if ($('stateAge')) $('stateAge').textContent = 'status unreachable';
      });
  }

  /* ── count-up tiles ─────────────────────────────────────── */
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    var dec = parseInt(el.getAttribute('data-dec') || '0', 10);
    if (isNaN(target)) return;
    if (reduced) { el.textContent = target.toFixed(dec); return; }

    var dur = 1100, t0 = null;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * eased).toFixed(dec);
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toFixed(dec);
    }
    requestAnimationFrame(step);
  }

  function watchCounters() {
    var nodes = document.querySelectorAll('[data-count]');
    if (!('IntersectionObserver' in window)) {
      Array.prototype.forEach.call(nodes, countUp);
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        countUp(e.target);
        io.unobserve(e.target);
      });
    }, { threshold: 0.4 });
    Array.prototype.forEach.call(nodes, function (n) { io.observe(n); });
  }

  /* ── scroll reveals (fallback only) ─────────────────────── */
  function watchReveals() {
    var supported = window.CSS && CSS.supports && CSS.supports('animation-timeline', 'view()');
    var nodes = document.querySelectorAll('.reveal');
    if (reduced || supported) return;
    if (!('IntersectionObserver' in window)) {
      Array.prototype.forEach.call(nodes, function (n) { n.classList.add('in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('in');
        io.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });
    Array.prototype.forEach.call(nodes, function (n) { io.observe(n); });
  }

  /* ── one decode flourish, on the eyebrow only ───────────── */
  function scramble(el) {
    var final = el.textContent;
    var glyphs = '01<>/\\|_-=+*#$%&@';
    var frame = 0, total = final.length * 2 + 12;

    // rAF is frozen in a background tab; leave the real text in place there
    // rather than stranding the reader on a screenful of glyphs.
    if (document.hidden) return;
    document.addEventListener('visibilitychange', function stop() {
      if (!document.hidden) return;
      frame = total + 1;
      el.textContent = final;
      document.removeEventListener('visibilitychange', stop);
    });

    function tick() {
      var out = '', i;
      for (i = 0; i < final.length; i++) {
        var ch = final[i];
        if (ch === ' ') { out += ' '; continue; }
        if (i * 2 < frame) out += ch;
        else out += glyphs[Math.floor(Math.random() * glyphs.length)];
      }
      el.textContent = out;
      frame += 1;
      if (frame <= total) requestAnimationFrame(tick);
      else el.textContent = final;
    }
    tick();
  }

  /* ── boot ───────────────────────────────────────────────── */
  function boot() {
    watchReveals();
    watchCounters();

    var eyebrow = document.querySelector('[data-scramble]');
    if (eyebrow && !reduced) setTimeout(function () { scramble(eyebrow); }, 220);

    loadStatus();
    setInterval(function () { if (!document.hidden) loadStatus(); }, REFRESH_MS);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
