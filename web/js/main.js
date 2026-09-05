/* TradePulse.AI — page behaviour
   Reads the system's own read-only status API and renders what it says.
   Nothing on this page is hard-coded market data. */
(function () {
  'use strict';

  var STATUS_API = '/api/state';          // same-origin, behind CloudFront
  var REFRESH_MS = 5 * 60 * 1000;

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var nf2 = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var $ = function (id) { return document.getElementById(id); };

  var venue = null;   // kept so the live price can re-mark equity between polls

  /* ── helpers ────────────────────────────────────────────── */
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

  function bps(x) {
    // slippage is a fraction; basis points read better than five decimals
    return (x * 10000).toFixed(1) + ' bps';
  }

  /* ── the executing bot ──────────────────────────────────── */
  function renderVenue(v) {
    venue = v;

    var posEl = $('mPosition');
    if (posEl) {
      posEl.textContent = v.position_label || '—';
      posEl.setAttribute('data-pos',
        v.position > 0 ? 'long' : v.position < 0 ? 'short' : 'flat');
    }
    if ($('mEntry')) {
      $('mEntry').textContent = v.entry_fill ? '$' + nf2.format(v.entry_fill) : '—';
    }
    if ($('mOrder')) {
      var id = (window.TP_LAST_ORDER || '');
      $('mOrder').textContent = id ? '#' + id : '—';
    }
    if ($('mKill')) {
      var halted = v.killswitch && v.killswitch.halted;
      $('mKill').textContent = halted ? 'HALTED' : 'armed';
      $('mKill').style.color = halted ? 'var(--down)' : 'var(--up)';
    }
    // Commission is billed in BNB, which the book records OUTSIDE equity because
    // converting it would need a BNB price the book does not have. So the equity
    // above is honestly a little generous, and by exactly this much. Publishing a
    // number while hiding the reason it is slightly wrong is how a dashboard
    // starts lying politely.
    if ($('mFeesExt')) {
      var ext = (v.fees_external && v.fees_external.BNB) || 0;
      // The unit lives in the label, like every other row here. Repeating it in
      // the value made this the only line on the card that wrapped.
      $('mFeesExt').textContent = ext ? ext.toFixed(8) : 'none';
      $('mFeesExt').title = ext
        ? 'Charged by the exchange, deliberately not deducted from the equity above'
        : '';
    }

    if ($('stateAge')) $('stateAge').textContent = 'updated ' + relTime(v.updated_at);

    markEquity(null);
  }

  // Equity is (cash + qty × price). Marking it to the live price rather than
  // the last close is the difference between a number and a live number.
  function markEquity(livePrice) {
    if (!venue || !$('mEquity')) return;
    var px = livePrice || venue.last_price;
    if (!px) return;

    var eq = (venue.cash || 0) + (venue.qty || 0) * px;
    var initial = venue.initial_capital || 0;
    $('mEquity').textContent = '$' + nf2.format(eq);

    var ret = initial ? (eq / initial - 1) * 100 : 0;
    $('mEquity').style.color = ret > 0 ? 'var(--up)' : ret < 0 ? 'var(--down)' : '';
  }

  window.TP_MARK = markEquity;   // chart.js calls this on every price tick

  /* ── execution quality ──────────────────────────────────── */
  function renderExecution(fills, gate) {
    if (!fills || !fills.length) return;
    var f = fills[0];
    window.TP_LAST_ORDER = f.order_id;

    if ($('slipAssumed')) $('slipAssumed').textContent = bps(f.slippage_assumed || 0);
    if ($('slipActual')) $('slipActual').textContent = bps(f.slippage_actual || 0);

    if ($('slipRatio') && f.slippage_assumed) {
      var ratio = (f.slippage_actual / f.slippage_assumed);
      $('slipRatio').textContent = ratio.toFixed(1) + '× the assumption';
    }
    if ($('gateCount')) {
      $('gateCount').textContent = gate.collected + ' of ' + gate.required + ' fills collected';
    }

    var body = $('fillsBody');
    if (!body) return;
    body.textContent = '';
    fills.forEach(function (x) {
      var tr = document.createElement('tr');
      [
        x.order_id,
        String(x.time || '').slice(0, 16),
        x.qty,
        x.assumed_price ? '$' + nf2.format(x.assumed_price) : '—',
        x.actual_price ? '$' + nf2.format(x.actual_price) : '—',
        bps(x.slippage_actual || 0)
      ].forEach(function (val, i) {
        var cell = document.createElement(i === 0 ? 'th' : 'td');
        if (i === 0) cell.setAttribute('scope', 'row');
        cell.textContent = val;
        tr.appendChild(cell);
      });
      body.appendChild(tr);
    });
    var wrap = $('fillsWrap');
    if (wrap) wrap.hidden = false;
  }

  /* ── decision tape ──────────────────────────────────────── */
  function renderTape(decisions) {
    var run = $('tapeRun');
    if (!run || !decisions || !decisions.length) return;

    var cells = decisions.slice().reverse().map(function (d) {
      var act = d.action || 'HOLD';
      var when = String(d.bar || '').slice(0, 16);
      var px = +d.price;
      return '<span class="tape__cell">' +
        '<span class="tape__date">' + when + '</span>' +
        '<span class="tape__px">' + (isFinite(px) ? nf2.format(px) : '—') + '</span>' +
        '<span class="tape__act" data-a="' + act + '">' + act + '</span>' +
        '</span>';
    }).join('');

    run.innerHTML = cells + cells;   // duplicated: the marquee loops at -50%
  }

  function loadStatus() {
    fetch(STATUS_API, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (d) {
        renderExecution(d.fills, d.gate || {});
        if (d.venue) renderVenue(d.venue);
        renderTape(d.decisions);
        if (window.TP && d.fills) window.TP.setFills(d.fills);
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
