import { useState, useEffect, useCallback } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Search, TrendingUp, TrendingDown, RefreshCw, BarChart3, ArrowUpRight, ArrowDownRight, Loader2 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const NIFTY_50 = [
  "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN","BHARTIARTL","ITC","KOTAKBANK",
  "LT","AXISBANK","BAJFINANCE","MARUTI","ASIANPAINT","WIPRO","HCLTECH","TATAMOTORS","SUNPHARMA","TITAN",
  "ULTRACEMCO","NESTLEIND","BAJAJFINSV","POWERGRID","NTPC","ONGC","JSWSTEEL","TATASTEEL","ADANIENT","ADANIPORTS",
  "TECHM","INDUSINDBK","HDFCLIFE","SBILIFE","DIVISLAB","CIPLA","GRASIM","APOLLOHOSP","EICHERMOT","DRREDDY",
  "HEROMOTOCO","COALINDIA","BPCL","BRITANNIA","BAJAJ-AUTO","TATACONSUM","M&M","HINDALCO","SHRIRAMFIN","LTIM",
];

interface StockQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  open: number;
  high: number;
  low: number;
  prevClose: number;
  volume: string;
  exchange: string;
}

interface IndexQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  prevClose: number;
}

interface StockHistory { date: string; close: number; }

const formatNum = (n: number) => n?.toLocaleString("en-IN", { maximumFractionDigits: 2 });

const API_URL = `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/stock-data`;
const AUTH_HEADERS = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY}`,
};

const LiveMarket = () => {
  const [query, setQuery] = useState("");
  const [stocks, setStocks] = useState<StockQuote[]>([]);
  const [indices, setIndices] = useState<IndexQuote[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStock, setSelectedStock] = useState<StockQuote | null>(null);
  const [history, setHistory] = useState<StockHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [searchSymbol, setSearchSymbol] = useState("");
  const [searchResult, setSearchResult] = useState<StockQuote | null>(null);
  const [searchHistory, setSearchHistory] = useState<StockHistory[]>([]);
  const [searching, setSearching] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [stocksRes, indicesRes] = await Promise.all([
        fetch(API_URL, { method: "POST", headers: AUTH_HEADERS, body: JSON.stringify({ action: "quotes", symbols: NIFTY_50 }) }),
        fetch(API_URL, { method: "POST", headers: AUTH_HEADERS, body: JSON.stringify({ action: "indices" }) }),
      ]);
      if (stocksRes.ok) {
        const data = await stocksRes.json();
        setStocks(data.quotes || []);
      }
      if (indicesRes.ok) {
        const data = await indicesRes.json();
        setIndices(data.indices || []);
      }
      setLastUpdated(new Date());
    } catch (e) {
      console.error("Failed to fetch", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const fetchHistory = async (symbol: string) => {
    setHistoryLoading(true);
    try {
      const res = await fetch(API_URL, { method: "POST", headers: AUTH_HEADERS, body: JSON.stringify({ action: "history", symbol }) });
      if (res.ok) { const data = await res.json(); setHistory(data.history || []); }
    } catch (e) { console.error(e); } finally { setHistoryLoading(false); }
  };

  const handleSelect = (stock: StockQuote) => {
    setSelectedStock(stock);
    fetchHistory(stock.symbol);
  };

  const handleSearch = async () => {
    const sym = searchSymbol.trim().toUpperCase();
    if (!sym) return;
    setSearching(true);
    setSearchResult(null);
    try {
      const res = await fetch(API_URL, { method: "POST", headers: AUTH_HEADERS, body: JSON.stringify({ action: "search", symbol: sym }) });
      if (res.ok) {
        const data = await res.json();
        setSearchResult(data.quote);
        setSearchHistory(data.history || []);
      }
    } catch (e) { console.error(e); } finally { setSearching(false); }
  };

  const filtered = stocks.filter(
    (s) => s.symbol?.toLowerCase().includes(query.toLowerCase()) || s.name?.toLowerCase().includes(query.toLowerCase())
  );

  const gainers = [...stocks].filter((s) => s.changePct > 0).sort((a, b) => b.changePct - a.changePct).slice(0, 5);
  const losers = [...stocks].filter((s) => s.changePct < 0).sort((a, b) => a.changePct - b.changePct).slice(0, 5);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-24 pb-16 px-4 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-wrap items-end justify-between gap-4 mb-6 animate-fade-up">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold"><span className="gradient-text">Live Market</span></h1>
            <p className="text-muted-foreground mt-1">Real-time NSE stock prices • Nifty 50 stocks</p>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && <span className="text-xs text-muted-foreground">Updated {lastUpdated.toLocaleTimeString()}</span>}
            <Button size="sm" variant="outline" onClick={fetchAll} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
            </Button>
          </div>
        </div>

        {/* Market Indices */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6 animate-fade-up">
          {indices.map((idx) => (
            <Card key={idx.symbol} className="overflow-hidden">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground font-medium">{idx.symbol}</p>
                <p className="text-xl font-bold font-sans">{formatNum(idx.price)}</p>
                <span className={`text-sm font-medium flex items-center gap-1 ${idx.changePct >= 0 ? "text-secondary" : "text-destructive"}`}>
                  {idx.changePct >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  {idx.changePct >= 0 ? "+" : ""}{formatNum(idx.change)} ({idx.changePct >= 0 ? "+" : ""}{idx.changePct?.toFixed(2)}%)
                </span>
              </CardContent>
            </Card>
          ))}
          {indices.length === 0 && !loading && (
            <>
              <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">NIFTY 50</p><p className="text-sm text-muted-foreground">Loading...</p></CardContent></Card>
              <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">SENSEX</p><p className="text-sm text-muted-foreground">Loading...</p></CardContent></Card>
            </>
          )}
        </div>

        {/* Search Any Stock */}
        <Card className="mb-6 animate-fade-up">
          <CardContent className="p-4">
            <p className="text-sm font-semibold mb-2">🔍 Search Any NSE/BSE Stock</p>
            <div className="flex gap-2">
              <Input
                placeholder="Enter stock symbol (e.g. ZOMATO, IRCTC, PAYTM)..."
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="flex-1"
              />
              <Button onClick={handleSearch} disabled={searching || !searchSymbol.trim()} className="gradient-primary text-white">
                {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              </Button>
            </div>
            {searchResult && (
              <div className="mt-4 grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-bold font-sans">{searchResult.symbol}</h3>
                      <p className="text-xs text-muted-foreground">{searchResult.name}</p>
                      <Badge variant="outline" className="text-[10px] mt-1">{searchResult.exchange}</Badge>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold font-sans">₹{formatNum(searchResult.price)}</p>
                      <span className={`text-sm ${searchResult.changePct >= 0 ? "text-secondary" : "text-destructive"}`}>
                        {searchResult.changePct >= 0 ? "▲" : "▼"} {formatNum(Math.abs(searchResult.change))} ({searchResult.changePct >= 0 ? "+" : ""}{searchResult.changePct?.toFixed(2)}%)
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border">
                    <div><span className="text-muted-foreground">Open</span><p className="font-bold">₹{formatNum(searchResult.open)}</p></div>
                    <div><span className="text-muted-foreground">Prev Close</span><p className="font-bold">₹{formatNum(searchResult.prevClose)}</p></div>
                    <div><span className="text-muted-foreground">High</span><p className="font-bold text-secondary">₹{formatNum(searchResult.high)}</p></div>
                    <div><span className="text-muted-foreground">Low</span><p className="font-bold text-destructive">₹{formatNum(searchResult.low)}</p></div>
                  </div>
                </div>
                {searchHistory.length > 0 && (
                  <ResponsiveContainer width="100%" height={160}>
                    <AreaChart data={searchHistory}>
                      <defs>
                        <linearGradient id="searchGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="hsl(207,72%,38%)" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="hsl(207,72%,38%)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(200,13%,88%)" />
                      <XAxis dataKey="date" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
                      <YAxis tick={{ fontSize: 9 }} domain={["auto", "auto"]} />
                      <Tooltip formatter={(v: number) => [`₹${formatNum(v)}`, "Close"]} />
                      <Area type="monotone" dataKey="close" stroke="hsl(207,72%,38%)" fill="url(#searchGrad)" strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Top Gainers / Losers */}
        <div className="grid md:grid-cols-2 gap-4 mb-6 animate-fade-up" style={{ animationDelay: "100ms" }}>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 font-sans"><ArrowUpRight className="w-4 h-4 text-secondary" /> Top Gainers</CardTitle>
            </CardHeader>
            <CardContent className="p-3 pt-0">
              {gainers.length === 0 && <p className="text-xs text-muted-foreground p-2">Loading...</p>}
              {gainers.map((s) => (
                <div key={s.symbol} className="flex justify-between items-center py-1.5 px-2 rounded hover:bg-muted/50 cursor-pointer text-sm" onClick={() => handleSelect(s)}>
                  <span className="font-medium font-sans">{s.symbol}</span>
                  <div className="text-right">
                    <span className="text-xs text-muted-foreground mr-2">₹{formatNum(s.price)}</span>
                    <span className="text-secondary font-medium">+{s.changePct?.toFixed(2)}%</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 font-sans"><ArrowDownRight className="w-4 h-4 text-destructive" /> Top Losers</CardTitle>
            </CardHeader>
            <CardContent className="p-3 pt-0">
              {losers.length === 0 && <p className="text-xs text-muted-foreground p-2">Loading...</p>}
              {losers.map((s) => (
                <div key={s.symbol} className="flex justify-between items-center py-1.5 px-2 rounded hover:bg-muted/50 cursor-pointer text-sm" onClick={() => handleSelect(s)}>
                  <span className="font-medium font-sans">{s.symbol}</span>
                  <div className="text-right">
                    <span className="text-xs text-muted-foreground mr-2">₹{formatNum(s.price)}</span>
                    <span className="text-destructive font-medium">{s.changePct?.toFixed(2)}%</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Filter */}
        <div className="relative mb-6 animate-fade-up" style={{ animationDelay: "150ms" }}>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Filter Nifty 50 stocks…" value={query} onChange={(e) => setQuery(e.target.value)} className="pl-10" />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Stock Table */}
          <div className="lg:col-span-2">
            <Card>
              <CardContent className="p-0">
                {loading ? (
                  <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
                ) : (
                  <div className="overflow-auto max-h-[600px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Name</TableHead>
                          <TableHead className="text-right">Price (₹)</TableHead>
                          <TableHead className="text-right">Change</TableHead>
                          <TableHead className="text-right">% Change</TableHead>
                          <TableHead className="text-right hidden sm:table-cell">Volume</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filtered.map((s) => (
                          <TableRow key={s.symbol} className="cursor-pointer hover:bg-muted/40" onClick={() => handleSelect(s)}>
                            <TableCell className="font-bold font-sans">{s.symbol}</TableCell>
                            <TableCell className="text-xs text-muted-foreground max-w-[120px] truncate">{s.name}</TableCell>
                            <TableCell className="text-right font-medium font-sans">₹{formatNum(s.price)}</TableCell>
                            <TableCell className={`text-right font-medium ${s.change >= 0 ? "text-secondary" : "text-destructive"}`}>
                              {s.change >= 0 ? "+" : ""}{formatNum(s.change)}
                            </TableCell>
                            <TableCell className={`text-right font-medium ${s.changePct >= 0 ? "text-secondary" : "text-destructive"}`}>
                              <span className="flex items-center justify-end gap-0.5">
                                {s.changePct >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                {s.changePct >= 0 ? "+" : ""}{s.changePct?.toFixed(2)}%
                              </span>
                            </TableCell>
                            <TableCell className="text-right text-xs hidden sm:table-cell">{s.volume}</TableCell>
                          </TableRow>
                        ))}
                        {filtered.length === 0 && (
                          <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">No stocks found</TableCell></TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-1">
            {selectedStock ? (
              <div className="space-y-4 animate-fade-up">
                <Card>
                  <CardContent className="p-5">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="text-xl font-bold font-sans">{selectedStock.symbol}</h3>
                        <p className="text-xs text-muted-foreground">{selectedStock.name}</p>
                        <Badge variant="outline" className="mt-1 text-[10px]">{selectedStock.exchange}</Badge>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold font-sans">₹{formatNum(selectedStock.price)}</p>
                        <span className={`text-sm ${selectedStock.changePct >= 0 ? "text-secondary" : "text-destructive"}`}>
                          {selectedStock.changePct >= 0 ? "▲" : "▼"} {formatNum(Math.abs(selectedStock.change))} ({selectedStock.changePct >= 0 ? "+" : ""}{selectedStock.changePct?.toFixed(2)}%)
                        </span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-xs mt-4 pt-3 border-t border-border">
                      <div><span className="text-muted-foreground">Open</span><p className="font-bold font-sans">₹{formatNum(selectedStock.open)}</p></div>
                      <div><span className="text-muted-foreground">Prev Close</span><p className="font-bold font-sans">₹{formatNum(selectedStock.prevClose)}</p></div>
                      <div><span className="text-muted-foreground">Day High</span><p className="font-bold font-sans text-secondary">₹{formatNum(selectedStock.high)}</p></div>
                      <div><span className="text-muted-foreground">Day Low</span><p className="font-bold font-sans text-destructive">₹{formatNum(selectedStock.low)}</p></div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2"><CardTitle className="text-sm font-sans">Price Chart (30 Days)</CardTitle></CardHeader>
                  <CardContent className="p-3">
                    {historyLoading ? (
                      <div className="flex items-center justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
                    ) : history.length > 0 ? (
                      <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={history}>
                          <defs>
                            <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="hsl(207,72%,38%)" stopOpacity={0.3} />
                              <stop offset="100%" stopColor="hsl(207,72%,38%)" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(200,13%,88%)" />
                          <XAxis dataKey="date" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
                          <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
                          <Tooltip formatter={(v: number) => [`₹${formatNum(v)}`, "Close"]} />
                          <Area type="monotone" dataKey="close" stroke="hsl(207,72%,38%)" fill="url(#histGrad)" strokeWidth={2} dot={false} />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="text-center text-xs text-muted-foreground py-10">No history available</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            ) : (
              <Card className="h-full flex items-center justify-center">
                <CardContent className="text-center py-20">
                  <BarChart3 className="w-12 h-12 mx-auto text-muted-foreground/40 mb-4" />
                  <p className="text-muted-foreground text-sm">Click on any stock to view details & chart</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default LiveMarket;
