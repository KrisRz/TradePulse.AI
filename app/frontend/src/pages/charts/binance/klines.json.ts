import type { APIRoute } from 'astro';

export const GET: APIRoute = async ({ url }) => {
  const symbol   = (url.searchParams.get('symbol')   ?? 'BTCUSDT').toUpperCase();
  const interval = (url.searchParams.get('interval') ?? '1m');
  const limit    = Math.min(Number(url.searchParams.get('limit') ?? '500'), 1000);

  const endpoint = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`;
  try {
    const res = await fetch(endpoint, { headers: { 'cache-control': 'no-cache' } });
    if (!res.ok) {
      return new Response(JSON.stringify({ error: 'Binance REST error', status: res.status }), { status: 502 });
    }
    const raw = (await res.json()) as any[];
    const candles = raw.map((d) => ({
      time: Math.floor(d[0] / 1000), // ms -> s
      open: +d[1], high: +d[2], low: +d[3], close: +d[4],
      volume: +d[5],
    }));
    return new Response(JSON.stringify({ symbol, interval, candles }), {
      headers: {
        'content-type': 'application/json; charset=utf-8',
        'cache-control': 'public, max-age=10'
      }
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Network failure' }), { status: 500 });
  }
};
