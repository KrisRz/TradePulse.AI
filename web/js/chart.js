/* TradePulse.AI — live chart
   Four-hour BTCUSDT candles from Binance REST, kept current over a websocket.
   The interval matches the bot that actually executes, so the EMA 20 / EMA 100
   computed here are the lines it decides on and the fill markers land on the
   exact bar the order went out. */
(function () {
  'use strict';

  var SYMBOL = 'BTCUSDT';
  var REST = 'https://api.binance.com/api/v3/klines?symbol=' + SYMBOL + '&interval=4h&limit=400';
  var WS = 'wss://stream.binance.com:9443/stream?streams=btcusdt@kline_4h/btcusdt@ticker';

  var C = {
    up: '#00A99C', down: '#F61C30',
    ema20: '#C18500', ema100: '#8A7BE8',
    panel: '#0E141B', grid: '#141D26', border: '#1B2733',
    text: '#8FA3B5', lo: '#5B6E80', hi: '#E4EDF6'
  };

  var host = document.getElementById('chartHost');
  var statusEl = document.getElementById('chartStatus');
  var capEl = document.getElementById('chartCap');
  var lastEl = document.getElementById('railLast');
  var chgEl = document.getElementById('railChg');
  var dotEl = document.getElementById('wsDot');
  var wsLabel = document.getElementById('wsLabel');

  var chart = null, candles = null, sEma20 = null, sEma100 = null;
  var bars = [];                 // [{time, open, high, low, close}]
  var ws = null, retries = 0, closedByUs = false, lastPrice = null;

  var nf = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function setConn(state, label) {
    if (dotEl) dotEl.setAttribute('data-state', state);
    if (wsLabel) wsLabel.textContent = label;
  }
  function setStatus(t) { if (statusEl) statusEl.textContent = t; }

  /* ── indicators ─────────────────────────────────────────── */
  function ema(series, period) {
    if (series.length < period) return [];
    var k = 2 / (period + 1), out = [], seed = 0, i;
    for (i = 0; i < period; i++) seed += series[i].close;
    var prev = seed / period;
    out.push({ time: series[period - 1].time, value: prev });
    for (i = period; i < series.length; i++) {
      prev = series[i].close * k + prev * (1 - k);
      out.push({ time: series[i].time, value: prev });
    }
    return out;
  }

  function redrawEmas() {
    if (!sEma20) return;
    sEma20.setData(ema(bars, 20));
    sEma100.setData(ema(bars, 100));
  }

  /* ── chart ──────────────────────────────────────────────── */
  function build() {
    if (!window.LightweightCharts || !host) return false;

    chart = LightweightCharts.createChart(host, {
      width: host.clientWidth,
      height: host.clientHeight,
      layout: {
        background: { type: 'solid', color: C.panel },
        textColor: C.text,
        fontFamily: "'Plex Mono', ui-monospace, monospace",
        fontSize: 11
      },
      grid: { vertLines: { color: C.grid }, horzLines: { color: C.grid } },
      rightPriceScale: { borderColor: C.border, scaleMargins: { top: 0.14, bottom: 0.14 } },
      timeScale: { borderColor: C.border, rightOffset: 14, barSpacing: 7, fixLeftEdge: true },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { color: C.lo, width: 1, style: 3, labelBackgroundColor: C.ema20 },
        horzLine: { color: C.lo, width: 1, style: 3, labelBackgroundColor: C.ema20 }
      },
      handleScale: { axisPressedMouseMove: false },
      localization: { priceFormatter: function (p) { return nf.format(p); } }
    });

    candles = chart.addCandlestickSeries({
      upColor: C.up, downColor: C.down,
      borderUpColor: C.up, borderDownColor: C.down,
      wickUpColor: C.up, wickDownColor: C.down,
      priceLineColor: C.ema20, priceLineStyle: 2
    });
    sEma100 = chart.addLineSeries({ color: C.ema100, lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    sEma20 = chart.addLineSeries({ color: C.ema20, lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });

    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        if (!chart) return;
        chart.applyOptions({ width: host.clientWidth, height: host.clientHeight });
        // The bar spacing fitContent picked belongs to the old width, so refit —
        // otherwise the candles sit in a narrow strip with dead space beside them.
        if (bars.length) fitWithPadding();
      }).observe(host);
    }
    return true;
  }

  // All bars, plus empty space on the right so a marker label near the last
  // bar has somewhere to render instead of being cut off by the price scale.
  function fitWithPadding() {
    if (!chart || !bars.length) return;
    chart.timeScale().setVisibleLogicalRange({ from: 0, to: bars.length + 12 });
  }

  /* ── history ────────────────────────────────────────────── */
  function loadHistory() {
    return fetch(REST, { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (rows) {
        bars = rows.map(function (k) {
          return {
            time: Math.floor(k[0] / 1000),
            open: +k[1], high: +k[2], low: +k[3], close: +k[4]
          };
        });
        candles.setData(bars);
        redrawEmas();
        // fit once the browser has settled the real element width
        requestAnimationFrame(function () {
          chart.applyOptions({ width: host.clientWidth, height: host.clientHeight });
          fitWithPadding();
        });
        setStatus(bars.length + ' bars');
        paintPrice(bars[bars.length - 1].close, null);
      });
  }

  /* ── live ───────────────────────────────────────────────── */
  function paintPrice(price, changePct) {
    if (!lastEl) return;
    if (lastPrice !== null && price !== lastPrice) {
      lastEl.classList.remove('tick-up', 'tick-down');
      void lastEl.offsetWidth;
      lastEl.classList.add(price > lastPrice ? 'tick-up' : 'tick-down');
    }
    lastPrice = price;
    lastEl.textContent = nf.format(price);
    if (window.TP_MARK) window.TP_MARK(price);
    if (changePct !== null && changePct !== undefined && chgEl) {
      var v = +changePct;
      chgEl.textContent = (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
      chgEl.className = 'rail__chg ' + (v >= 0 ? 'pos' : 'neg');
    }
  }

  function onKline(k) {
    var bar = {
      time: Math.floor(k.t / 1000),
      open: +k.o, high: +k.h, low: +k.l, close: +k.c
    };
    var last = bars[bars.length - 1];
    if (last && bar.time === last.time) bars[bars.length - 1] = bar;
    else if (!last || bar.time > last.time) bars.push(bar);
    else return;

    candles.update(bar);
    redrawEmas();
  }

  function connect() {
    if (document.hidden) return;               // don't hold a socket in a background tab
    closedByUs = false;
    setConn('wait', 'connecting');
    try { ws = new WebSocket(WS); } catch (e) { scheduleRetry(); return; }

    ws.onopen = function () { retries = 0; setConn('live', 'live'); };

    ws.onmessage = function (ev) {
      var msg;
      try { msg = JSON.parse(ev.data); } catch (e) { return; }
      var d = msg.data;
      if (!d) return;
      if (d.e === 'kline') onKline(d.k);
      else if (d.e === '24hrTicker') paintPrice(+d.c, +d.P);
    };

    ws.onerror = function () { try { ws.close(); } catch (e) {} };

    ws.onclose = function () {
      if (closedByUs) return;
      setConn('down', 'reconnecting');
      scheduleRetry();
    };
  }

  function scheduleRetry() {
    retries += 1;
    if (retries > 8) { setConn('down', 'offline'); return; }
    var wait = Math.min(30000, 1000 * Math.pow(2, retries - 1));
    setTimeout(connect, wait);
  }

  function disconnect() {
    closedByUs = true;
    if (ws) { try { ws.close(); } catch (e) {} ws = null; }
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { disconnect(); setConn('wait', 'paused'); }
    else if (!ws || ws.readyState > 1) { retries = 0; connect(); }
  });

  /* ── markers from the bot's own fill history ────────────── */
  function toBarTime(iso) {
    var ms = Date.parse(String(iso).replace(' ', 'T'));
    if (isNaN(ms)) return null;
    return Math.floor(ms / 14400000) * 14400;   // snap to the 4-hour bar
  }

  window.TP = {
    setFills: function (fills) {
      if (!candles || !fills || !fills.length) return;
      var marks = fills.map(function (f) {
        var t = toBarTime(f.time);
        if (!t) return null;
        var buy = (+f.side || 1) > 0;
        return {
          time: t,
          position: buy ? 'belowBar' : 'aboveBar',
          color: buy ? C.up : C.down,
          shape: buy ? 'arrowUp' : 'arrowDown',
          text: buy ? 'BUY' : 'SELL'
        };
      }).filter(Boolean);

      if (!marks.length) return;
      marks.sort(function (a, b) { return a.time - b.time; });
      candles.setMarkers(marks);

      if (capEl) {
        capEl.textContent = 'Marked from the venue fill log: ' + marks.length +
          (marks.length === 1 ? ' order' : ' orders') +
          ' the exchange actually filled, at the price it actually gave.';
      }
    }
  };

  /* ── boot ───────────────────────────────────────────────── */
  function fail(msg) {
    setStatus('unavailable');
    setConn('down', 'offline');
    if (host) {
      host.textContent = '';
      var box = document.createElement('div');
      box.className = 'chart-fail';
      box.textContent = 'Market data is not reachable from this network. ' + msg;
      host.appendChild(box);
    }
  }

  function boot() {
    if (!build()) { fail('The chart library did not load.'); return; }
    loadHistory().then(connect).catch(function (e) {
      fail('Binance returned: ' + e.message);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
