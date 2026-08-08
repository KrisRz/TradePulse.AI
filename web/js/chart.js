/* TradePulse.AI — live chart
   Daily BTCUSDT candles from Binance REST, kept current over a websocket.
   EMA 20 / EMA 100 are computed here from the same closed candles the bot
   uses, so the lines on screen are the lines it actually decides on. */
(function () {
  'use strict';

  var SYMBOL = 'BTCUSDT';
  var REST = 'https://api.binance.com/api/v3/klines?symbol=' + SYMBOL + '&interval=1d&limit=260';
  var WS = 'wss://stream.binance.com:9443/stream?streams=btcusdt@kline_1d/btcusdt@ticker';

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
      timeScale: { borderColor: C.border, rightOffset: 5, barSpacing: 7, fixLeftEdge: true },
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
        if (bars.length) chart.timeScale().fitContent();
      }).observe(host);
    }
    return true;
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
          chart.timeScale().fitContent();
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
    return Math.floor(ms / 86400000) * 86400;   // snap to the UTC daily bar
  }

  window.TP = {
    setTrades: function (trades) {
      if (!candles || !trades || !trades.length) return;
      var marks = [];
      trades.forEach(function (t) {
        var isLong = (+t.side || 1) > 0;
        var a = toBarTime(t.entry_time), b = toBarTime(t.exit_time);
        if (a) marks.push({
          time: a, position: 'belowBar', color: C.up, shape: 'arrowUp',
          text: (isLong ? 'BUY ' : 'SELL ') + nf.format(+t.entry_price)
        });
        if (b) marks.push({
          time: b, position: 'aboveBar',
          color: (+t.net_return >= 0 ? C.up : C.down), shape: 'arrowDown',
          text: 'EXIT ' + nf.format(+t.exit_price) + ' · ' + ((+t.net_return) * 100).toFixed(2) + '%'
        });
      });
      marks.sort(function (x, y) { return x.time - y.time; });
      candles.setMarkers(marks);
      if (capEl) {
        capEl.textContent = 'Markers show where the bot actually entered and exited — ' +
          trades.length + ' closed ' + (trades.length === 1 ? 'trade' : 'trades') +
          ' on the paper account.';
      }
    }
  };

  /* ── boot ───────────────────────────────────────────────── */
  function fail(msg) {
    setStatus('unavailable');
    setConn('down', 'offline');
    if (host) {
      host.innerHTML = '<div style="display:flex;height:100%;align-items:center;justify-content:center;' +
        'padding:2rem;text-align:center;color:#5B6E80;font-size:.82rem;line-height:1.7">' +
        'Market data is not reachable from this network.<br>' + msg + '</div>';
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
