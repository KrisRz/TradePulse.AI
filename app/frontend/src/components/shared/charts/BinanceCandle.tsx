import { useEffect, useRef } from 'preact/hooks';
import {
  createChart,
  CandlestickSeries,
  LineSeries, 
  HistogramSeries,
  type IChartApi,
  type CandlestickData,
  type HistogramData,
  type LineData
} from 'lightweight-charts';
import { getEnvironmentConfig } from '../../../config/environments';

type Props = {
  symbol?: string;      // 'BTCUSDT'
  interval?: string;    // '1m' | '5m' | '15m' | '1h' | ...
  height?: number;
  limit?: number;       // ilość świec do wczytania
};

function sma(values: number[], len: number): number[] {
  const out: number[] = []; let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i]; if (i >= len) sum -= values[i - len];
    out.push(i >= len - 1 ? sum / len : NaN);
  }
  return out;
}

export default function BinanceCandle({
  symbol = 'BTCUSDT', interval = '1m', height = 520, limit = 500,
}: Props) {
  const host = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!host.current) return;

    const chart = createChart(host.current, {
      autoSize: true,
      height,
      layout: { background: { color: '#0b1220' }, textColor: '#d1d5db' },
      grid: { vertLines: { color: '#1b2436' }, horzLines: { color: '#1b2436' } },
      rightPriceScale: { borderColor: '#2b3a55' },
      timeScale: { borderColor: '#2b3a55', secondsVisible: interval.endsWith('m') },
    });
    chartRef.current = chart;

    const candlesSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#ef4444',
      borderUpColor: '#22c55e', borderDownColor: '#ef4444',
      wickUpColor: '#22c55e', wickDownColor: '#ef4444',
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: 'vol',
      priceFormat: { type: 'volume' },
      base: 0,
    });
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    // REMOVED: MA lines and price line (only candlestick + volume)
    // const ma7  = chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2 });
    // const ma25 = chart.addSeries(LineSeries, { color: '#60a5fa', lineWidth: 2 });
    // const ma99 = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 2 });
    // const priceLine = candlesSeries.createPriceLine({ price: 0, color: '#93c5fd', lineWidth: 1 });

    let C: CandlestickData[] = [];
    let V: HistogramData[] = [];

    // REMOVED: MA calculation (only candlestick + volume)
    // const recomputeMA = () => {
    //   const closes = C.map(c => Number(c.close));
    //   const times  = C.map(c => c.time);
    //   const toLine = (arr: number[]): LineData[] =>
    //     arr.map((v, i) => ({ time: times[i], value: Number.isFinite(v) ? v : NaN }));
    //   ma7.setData(toLine(sma(closes, 7)));
    //   ma25.setData(toLine(sma(closes, 25)));
    //   ma99.setData(toLine(sma(closes, 99)));
    // };

    const load = async () => {
      try {
        console.log(`📊 [BinanceCandle] Fetching klines for ${symbol} ${interval}...`);
        // Use API base URL from environment config to work in both local (Nginx proxy) and AWS (direct App Runner)
        const config = getEnvironmentConfig();
        const url = `${config.api.base}/api/v1/market/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`;
        console.log(`📡 [BinanceCandle] URL: ${url}`);
        
        const r = await fetch(url);
        console.log(`📥 [BinanceCandle] Response status: ${r.status}`);
        
        if (!r.ok) {
          throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        }
        
        const data = await r.json();
        console.log(`📦 [BinanceCandle] Data received:`, data);
        console.log(`📦 [BinanceCandle] Klines count: ${data.klines?.length || 0}`);
        
        // Backend returns "klines" not "candles"!
        const { klines } = data;
        
        if (!klines || !Array.isArray(klines) || klines.length === 0) {
          console.error(`❌ [BinanceCandle] No klines data received:`, data);
          return;
        }
        
        console.log(`✅ [BinanceCandle] Processing ${klines.length} candles...`);

        // Backend returns open_time in milliseconds, lightweight-charts needs seconds
        C = klines.map((d: any) => ({ 
          time: Math.floor(d.open_time / 1000), 
          open: Number(d.open), 
          high: Number(d.high), 
          low: Number(d.low), 
          close: Number(d.close) 
        }));
        V = klines.map((d: any) => ({
          time: Math.floor(d.open_time / 1000), 
          value: Number(d.volume), 
          color: Number(d.close) >= Number(d.open) ? '#22c55e88' : '#ef444488'
        }));

        console.log(`📈 [BinanceCandle] Candlestick data:`, C.slice(0, 2));
        console.log(`📊 [BinanceCandle] Volume data:`, V.slice(0, 2));

        candlesSeries.setData(C);
        volumeSeries.setData(V);
        // REMOVED: MA calculation and price line
        // recomputeMA();
        // priceLine.applyOptions({ price: Number(C[C.length - 1].close) });
        chart.timeScale().fitContent();
        
        console.log(`✅ [BinanceCandle] Chart rendered successfully!`);
      } catch (error: any) {
        console.error(`❌ [BinanceCandle] Failed to load chart data:`, error);
        console.error(`❌ [BinanceCandle] Error details:`, {
          message: error?.message || 'Unknown error',
          stack: error?.stack || 'No stack trace'
        });
      }
    };

    load();

    // LIVE: Binance WebSocket
    console.log(`🔌 [BinanceCandle] Opening WebSocket for live updates...`);
    const ws = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${interval}`);
    ws.onopen = () => console.log(`✅ [BinanceCandle] WebSocket connected`);
    ws.onerror = (err) => console.error(`❌ [BinanceCandle] WebSocket error:`, err);
    ws.onclose = () => console.log(`🔌 [BinanceCandle] WebSocket closed`);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      const k = msg?.k; if (!k) return;
      const t = Math.floor(k.t / 1000);

      const bar: CandlestickData = { time: t, open: +k.o, high: +k.h, low: +k.l, close: +k.c };
      const vol: HistogramData  = { time: t, value: +k.v, color: +k.c >= +k.o ? '#22c55e88' : '#ef444488' };

      const last = C[C.length - 1];
      if (last && last.time === bar.time) {
        C[C.length - 1] = bar; V[V.length - 1] = vol;
        candlesSeries.update(bar); volumeSeries.update(vol);
      } else {
        C.push(bar); V.push(vol);
        candlesSeries.update(bar); volumeSeries.update(vol);
      }
      // REMOVED: MA calculation and price line updates
      // priceLine.applyOptions({ price: Number(bar.close) });
      // recomputeMA();
    };

    const ro = new ResizeObserver(() => chart.timeScale().fitContent());
    ro.observe(host.current);

    return () => { ws.close(); ro.disconnect(); chart.remove(); chartRef.current = null; };
  }, [symbol, interval, height, limit]);

  return <div ref={host} style={`height:${height}px`} class="rounded-2xl shadow-lg" />;
}
