import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown } from "lucide-react";

interface TickerItem {
  symbol: string;
  price: number;
  changePct: number;
}

const NIFTY_50 = [
  "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN","BHARTIARTL","ITC","KOTAKBANK",
  "LT","AXISBANK","BAJFINANCE","MARUTI","ASIANPAINT","WIPRO","HCLTECH","TATAMOTORS","SUNPHARMA","TITAN",
  "ULTRACEMCO","NESTLEIND","BAJAJFINSV","POWERGRID","NTPC","ONGC","JSWSTEEL","TATASTEEL","ADANIENT","ADANIPORTS",
  "TECHM","INDUSINDBK","HDFCLIFE","SBILIFE","DIVISLAB","CIPLA","GRASIM","APOLLOHOSP","EICHERMOT","DRREDDY",
  "HEROMOTOCO","COALINDIA","BPCL","BRITANNIA","BAJAJ-AUTO","TATACONSUM","M&M","HINDALCO","SHRIRAMFIN","LTIM",
];

const StockTicker = () => {
  const [items, setItems] = useState<TickerItem[]>([]);

  useEffect(() => {
    const fetchTicker = async () => {
      try {
        const res = await fetch(
          `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/stock-data`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY}`,
            },
            body: JSON.stringify({ action: "quotes", symbols: NIFTY_50 }),
          }
        );
        if (res.ok) {
          const data = await res.json();
          const quotes = (data.quotes || []).map((q: any) => ({
            symbol: q.symbol,
            price: q.price,
            changePct: q.changePct,
          }));
          setItems(quotes);
        }
      } catch (e) {
        console.error("Ticker fetch failed", e);
      }
    };
    fetchTicker();
    const interval = setInterval(fetchTicker, 60000); // refresh every 60s
    return () => clearInterval(interval);
  }, []);

  if (items.length === 0) return null;

  // Duplicate for seamless loop
  const tickerContent = [...items, ...items];

  return (
    <div className="w-full overflow-hidden bg-card/80 backdrop-blur border-b border-border">
      <div className="ticker-scroll flex items-center gap-6 py-2 px-4 whitespace-nowrap">
        {tickerContent.map((item, i) => (
          <a
            key={`${item.symbol}-${i}`}
            href="/live-market"
            className="inline-flex items-center gap-1.5 text-xs font-medium shrink-0 hover:opacity-80 transition-opacity"
          >
            <span className="text-foreground font-sans font-bold">{item.symbol}</span>
            <span className="text-muted-foreground">₹{item.price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
            <span className={`flex items-center gap-0.5 ${item.changePct >= 0 ? "text-secondary" : "text-destructive"}`}>
              {item.changePct >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {item.changePct >= 0 ? "+" : ""}{item.changePct.toFixed(2)}%
            </span>
          </a>
        ))}
      </div>
    </div>
  );
};

export default StockTicker;
