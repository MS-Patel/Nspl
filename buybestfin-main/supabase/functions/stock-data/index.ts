import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

// Yahoo Finance API for Indian stocks
async function fetchYahooQuote(symbol: string, suffix = ".NS"): Promise<any> {
  const yfSymbol = `${symbol}${suffix}`;
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${yfSymbol}?range=1d&interval=1m&includePrePost=false`;
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });
    if (!res.ok) return null;
    const data = await res.json();
    const result = data?.chart?.result?.[0];
    if (!result) return null;

    const meta = result.meta;
    const price = meta.regularMarketPrice;
    const prevClose = meta.chartPreviousClose || meta.previousClose;
    const change = price - prevClose;
    const changePct = (change / prevClose) * 100;

    return {
      symbol,
      name: meta.shortName || meta.longName || symbol,
      price: Math.round(price * 100) / 100,
      change: Math.round(change * 100) / 100,
      changePct: Math.round(changePct * 100) / 100,
      open: meta.regularMarketOpen || price,
      high: meta.regularMarketDayHigh || price,
      low: meta.regularMarketDayLow || price,
      prevClose: Math.round(prevClose * 100) / 100,
      volume: meta.regularMarketVolume
        ? (meta.regularMarketVolume / 100000).toFixed(2) + "L"
        : "N/A",
      exchange: suffix === ".NS" ? "NSE" : "BSE",
    };
  } catch (e) {
    console.error(`Error fetching ${symbol}:`, e);
    return null;
  }
}

// Fetch index quote (^NSEI for Nifty, ^BSESN for Sensex)
async function fetchIndexQuote(symbol: string): Promise<any> {
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1d&interval=5m&includePrePost=false`;
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });
    if (!res.ok) return null;
    const data = await res.json();
    const result = data?.chart?.result?.[0];
    if (!result) return null;

    const meta = result.meta;
    const price = meta.regularMarketPrice;
    const prevClose = meta.chartPreviousClose || meta.previousClose;
    const change = price - prevClose;
    const changePct = (change / prevClose) * 100;

    return {
      symbol: symbol === "^NSEI" ? "NIFTY 50" : "SENSEX",
      name: meta.shortName || meta.longName || symbol,
      price: Math.round(price * 100) / 100,
      change: Math.round(change * 100) / 100,
      changePct: Math.round(changePct * 100) / 100,
      prevClose: Math.round(prevClose * 100) / 100,
    };
  } catch (e) {
    console.error(`Error fetching index ${symbol}:`, e);
    return null;
  }
}

async function fetchYahooHistory(symbol: string): Promise<any[]> {
  const yfSymbol = `${symbol}.NS`;
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${yfSymbol}?range=1mo&interval=1d`;
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });
    if (!res.ok) return [];
    const data = await res.json();
    const result = data?.chart?.result?.[0];
    if (!result) return [];

    const timestamps = result.timestamp || [];
    const closes = result.indicators?.quote?.[0]?.close || [];

    return timestamps.map((ts: number, i: number) => ({
      date: new Date(ts * 1000).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
      close: Math.round((closes[i] || 0) * 100) / 100,
    })).filter((d: any) => d.close > 0);
  } catch (e) {
    console.error(`Error fetching history for ${symbol}:`, e);
    return [];
  }
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { action, symbols, symbol } = await req.json();

    if (action === "quotes" && symbols?.length) {
      // Fetch all quotes in parallel, max 55
      const toFetch = symbols.slice(0, 55);
      const results = await Promise.all(toFetch.map((s: string) => fetchYahooQuote(s)));
      const quotes = results.filter(Boolean);

      return new Response(JSON.stringify({ quotes }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (action === "search" && symbol) {
      // Search a single symbol by trying NSE first, then BSE
      let quote = await fetchYahooQuote(symbol, ".NS");
      if (!quote) quote = await fetchYahooQuote(symbol, ".BO");
      if (!quote) {
        return new Response(JSON.stringify({ error: "Stock not found" }), {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      const history = await fetchYahooHistory(symbol);
      return new Response(JSON.stringify({ quote, history }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (action === "indices") {
      const [nifty, sensex] = await Promise.all([
        fetchIndexQuote("^NSEI"),
        fetchIndexQuote("^BSESN"),
      ]);
      return new Response(JSON.stringify({ indices: [nifty, sensex].filter(Boolean) }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    if (action === "history" && symbol) {
      const history = await fetchYahooHistory(symbol);
      return new Response(JSON.stringify({ history }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ error: "Invalid action" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error:", error);
    return new Response(JSON.stringify({ error: "Internal error" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
