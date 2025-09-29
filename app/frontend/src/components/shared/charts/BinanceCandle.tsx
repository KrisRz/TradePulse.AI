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

    const ma7  = chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2 });
    const ma25 = chart.addSeries(LineSeries, { color: '#60a5fa', lineWidth: 2 });
    const ma99 = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 2 });

    const priceLine = candlesSeries.createPriceLine({ price: 0, color: '#93c5fd', lineWidth: 1 });

    let C: CandlestickData[] = [];
    let V: HistogramData[] = [];

    const recomputeMA = () => {
      const closes = C.map(c => Number(c.close));
      const times  = C.map(c => c.time);
      const toLine = (arr: number[]): LineData[] =>
        arr.map((v, i) => ({ time: times[i], value: Number.isFinite(v) ? v : NaN }));
      ma7.setData(toLine(sma(closes, 7)));
      ma25.setData(toLine(sma(closes, 25)));
      ma99.setData(toLine(sma(closes, 99)));
    };

    const load = async () => {
      const r = await fetch(`https://api.tradepulseai.co.uk/api/v1/market/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`);
      const { candles } = await r.json();

      C = candles.map((d: any) => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }));
      V = candles.map((d: any) => ({
        time: d.time, value: d.volume, color: d.close >= d.open ? '#22c55e88' : '#ef444488'
      }));

      candlesSeries.setData(C);
      volumeSeries.setData(V);
      recomputeMA();
      priceLine.applyOptions({ price: Number(C[C.length - 1].close) });
      chart.timeScale().fitContent();
    };

    load();

    // LIVE: Binance WebSocket
    const ws = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${interval}`);
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
      priceLine.applyOptions({ price: Number(bar.close) });
      recomputeMA();
    };

    const ro = new ResizeObserver(() => chart.timeScale().fitContent());
    ro.observe(host.current);

    return () => { ws.close(); ro.disconnect(); chart.remove(); chartRef.current = null; };
  }, [symbol, interval, height, limit]);

  return <div ref={host} style={`height:${height}px`} class="rounded-2xl shadow-lg" />;
}
