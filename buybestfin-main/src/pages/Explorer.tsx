import { useState, useEffect, useMemo, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import Navbar from "@/components/Navbar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Search, TrendingUp, TrendingDown, ArrowLeft, BarChart3, Info, Calendar, IndianRupee, GitCompareArrows, X, Filter, ChevronDown, ChevronUp } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, Legend } from "recharts";

// Types
interface MFScheme {
  schemeCode: number;
  schemeName: string;
}

interface NAVData {
  date: string;
  nav: string;
}

interface SchemeDetails {
  meta: {
    fund_house: string;
    scheme_type: string;
    scheme_category: string;
    scheme_code: number;
    scheme_name: string;
  };
  data: NAVData[];
}

// Known AMCs for filtering
const PARTNER_AMCS = [
  "360 ONE Mutual Fund",
  "Aditya Birla Sun Life Mutual Fund",
  "Axis Mutual Fund",
  "Bajaj Finserv Mutual Fund",
  "Bandhan Mutual Fund",
  "Canara Robeco Mutual Fund",
  "DSP Mutual Fund",
  "Edelweiss Mutual Fund",
  "Franklin Templeton Mutual Fund",
  "HDFC Mutual Fund",
  "HSBC Mutual Fund",
  "ICICI Prudential Mutual Fund",
  "Invesco Mutual Fund",
  "Kotak Mahindra Mutual Fund",
  "Mirae Asset Mutual Fund",
  "Motilal Oswal Mutual Fund",
  "Nippon India Mutual Fund",
  "PPFAS Mutual Fund",
  "Quant Mutual Fund",
  "Quantum Mutual Fund",
  "SBI Mutual Fund",
  "Sundaram Mutual Fund",
  "Tata Mutual Fund",
  "Trust Mutual Fund",
  "UTI Mutual Fund",
];

const SCHEME_TYPES = ["All Types", "Open Ended", "Close Ended", "Interval Fund"];

const SCHEME_CATEGORIES = ["All Categories", "Equity", "Debt", "Hybrid", "Solution Oriented", "Other"];

const SUB_CATEGORIES = [
  "All Sub-Categories",
  "Large Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Large & Mid Cap",
  "ELSS", "Index", "Sectoral", "Thematic", "Value",
  "Liquid", "Ultra Short", "Short Duration", "Corporate Bond", "Gilt", "Dynamic Bond",
  "Balanced", "Aggressive Hybrid", "Conservative Hybrid", "Arbitrage", "Multi Asset",
  "Retirement", "Children",
];

// Fetch all MF schemes
const fetchAllSchemes = async (): Promise<MFScheme[]> => {
  const res = await fetch("https://api.mfapi.in/mf");
  if (!res.ok) throw new Error("Failed to fetch schemes");
  return res.json();
};

// Fetch scheme details
const fetchSchemeDetails = async (code: number): Promise<SchemeDetails> => {
  const res = await fetch(`https://api.mfapi.in/mf/${code}`);
  if (!res.ok) throw new Error("Failed to fetch scheme details");
  return res.json();
};

// Helper to guess AMC from scheme name
const guessAMC = (name: string): string => {
  const lower = name.toLowerCase();
  if (lower.includes("360 one") || lower.includes("360one") || lower.includes("iifl")) return "360 ONE Mutual Fund";
  if (lower.includes("aditya birla") || lower.includes("absl") || lower.includes("birla sun life")) return "Aditya Birla Sun Life Mutual Fund";
  if (lower.includes("axis")) return "Axis Mutual Fund";
  if (lower.includes("bajaj finserv")) return "Bajaj Finserv Mutual Fund";
  if (lower.includes("bandhan")) return "Bandhan Mutual Fund";
  if (lower.includes("canara")) return "Canara Robeco Mutual Fund";
  if (lower.includes("dsp")) return "DSP Mutual Fund";
  if (lower.includes("edelweiss")) return "Edelweiss Mutual Fund";
  if (lower.includes("franklin") || lower.includes("templeton")) return "Franklin Templeton Mutual Fund";
  if (lower.includes("hdfc")) return "HDFC Mutual Fund";
  if (lower.includes("hsbc")) return "HSBC Mutual Fund";
  if (lower.includes("icici")) return "ICICI Prudential Mutual Fund";
  if (lower.includes("invesco")) return "Invesco Mutual Fund";
  if (lower.includes("kotak")) return "Kotak Mahindra Mutual Fund";
  if (lower.includes("mirae")) return "Mirae Asset Mutual Fund";
  if (lower.includes("motilal")) return "Motilal Oswal Mutual Fund";
  if (lower.includes("nippon") || lower.includes("reliance")) return "Nippon India Mutual Fund";
  if (lower.includes("ppfas") || lower.includes("parag parikh")) return "PPFAS Mutual Fund";
  if (lower.includes("quant")) return "Quant Mutual Fund";
  if (lower.includes("quantum")) return "Quantum Mutual Fund";
  if (lower.includes("sbi")) return "SBI Mutual Fund";
  if (lower.includes("sundaram")) return "Sundaram Mutual Fund";
  if (lower.includes("tata")) return "Tata Mutual Fund";
  if (lower.includes("trust mf") || lower.includes("trust mutual")) return "Trust Mutual Fund";
  if (lower.includes("uti ")) return "UTI Mutual Fund";
  return "Other";
};

const guessCategory = (name: string): string => {
  const lower = name.toLowerCase();
  if (lower.includes("equity") || lower.includes("large cap") || lower.includes("mid cap") || lower.includes("small cap") || lower.includes("flexi") || lower.includes("multi cap") || lower.includes("elss") || lower.includes("index") || lower.includes("nifty") || lower.includes("sensex") || lower.includes("sectoral") || lower.includes("thematic") || lower.includes("value") || lower.includes("focused") || lower.includes("contra")) return "Equity";
  if (lower.includes("debt") || lower.includes("liquid") || lower.includes("money market") || lower.includes("gilt") || lower.includes("bond") || lower.includes("overnight") || lower.includes("ultra short") || lower.includes("short duration") || lower.includes("corporate") || lower.includes("dynamic bond") || lower.includes("floater") || lower.includes("credit risk")) return "Debt";
  if (lower.includes("hybrid") || lower.includes("balanced") || lower.includes("aggressive") || lower.includes("conservative") || lower.includes("arbitrage") || lower.includes("equity savings") || lower.includes("multi asset")) return "Hybrid";
  if (lower.includes("retirement") || lower.includes("children") || lower.includes("solution")) return "Solution Oriented";
  return "Other";
};

const guessSubCategory = (name: string): string => {
  const lower = name.toLowerCase();
  if (lower.includes("large & mid") || lower.includes("large and mid")) return "Large & Mid Cap";
  if (lower.includes("large cap") || lower.includes("largecap")) return "Large Cap";
  if (lower.includes("mid cap") || lower.includes("midcap")) return "Mid Cap";
  if (lower.includes("small cap") || lower.includes("smallcap")) return "Small Cap";
  if (lower.includes("flexi cap") || lower.includes("flexicap")) return "Flexi Cap";
  if (lower.includes("multi cap") || lower.includes("multicap")) return "Multi Cap";
  if (lower.includes("elss") || lower.includes("tax sav")) return "ELSS";
  if (lower.includes("index") || lower.includes("nifty") || lower.includes("sensex") || lower.includes("etf")) return "Index";
  if (lower.includes("sectoral") || lower.includes("pharma") || lower.includes("banking") || lower.includes("infra") || lower.includes("technology") || lower.includes("consumption")) return "Sectoral";
  if (lower.includes("thematic") || lower.includes("esg") || lower.includes("manufacturing") || lower.includes("innovation") || lower.includes("quant")) return "Thematic";
  if (lower.includes("value") || lower.includes("contra")) return "Value";
  if (lower.includes("liquid")) return "Liquid";
  if (lower.includes("ultra short")) return "Ultra Short";
  if (lower.includes("short duration") || lower.includes("short term")) return "Short Duration";
  if (lower.includes("corporate bond")) return "Corporate Bond";
  if (lower.includes("gilt")) return "Gilt";
  if (lower.includes("dynamic bond")) return "Dynamic Bond";
  if (lower.includes("balanced") || lower.includes("balanced advantage")) return "Balanced";
  if (lower.includes("aggressive hybrid")) return "Aggressive Hybrid";
  if (lower.includes("conservative hybrid")) return "Conservative Hybrid";
  if (lower.includes("arbitrage")) return "Arbitrage";
  if (lower.includes("multi asset")) return "Multi Asset";
  if (lower.includes("retirement")) return "Retirement";
  if (lower.includes("children")) return "Children";
  return "";
};

const guessSchemeType = (name: string): string => {
  const lower = name.toLowerCase();
  if (lower.includes("close ended") || lower.includes("close-ended")) return "Close Ended";
  if (lower.includes("interval")) return "Interval Fund";
  return "Open Ended";
};

// Period options for chart
const CHART_PERIODS = [
  { label: "1M", days: 30 },
  { label: "3M", days: 90 },
  { label: "6M", days: 180 },
  { label: "1Y", days: 365 },
  { label: "3Y", days: 1095 },
  { label: "5Y", days: 1825 },
  { label: "All", days: 0 },
];

const COMPARE_COLORS = ["hsl(215, 80%, 28%)", "hsl(160, 50%, 40%)", "hsl(38, 92%, 50%)", "hsl(0, 84%, 60%)"];

// Mini component to show fund performance in the list
const FundCardPerf = ({ schemeCode }: { schemeCode: number }) => {
  const { data, isLoading } = useQuery({
    queryKey: ["mf-perf", schemeCode],
    queryFn: () => fetchSchemeDetails(schemeCode),
    staleTime: 1000 * 60 * 30,
  });

  if (isLoading) return <div className="flex gap-2 items-center"><Skeleton className="h-4 w-16" /><Skeleton className="h-4 w-10" /><Skeleton className="h-4 w-10" /></div>;
  if (!data?.data?.length) return <span className="text-xs text-muted-foreground">N/A</span>;

  const d = data.data;
  const currentNav = parseFloat(d[0].nav);
  const prevNav = d.length > 1 ? parseFloat(d[1].nav) : currentNav;
  const dayChange = prevNav > 0 ? ((currentNav - prevNav) / prevNav) * 100 : 0;

  const getReturn = (daysAgo: number) => {
    const target = d.find((_, i) => i >= daysAgo) || d[d.length - 1];
    const oldNav = parseFloat(target.nav);
    return oldNav > 0 ? ((currentNav - oldNav) / oldNav) * 100 : 0;
  };

  const periods = [
    { label: "1M", val: getReturn(22) },
    { label: "6M", val: getReturn(132) },
    { label: "1Y", val: getReturn(252) },
    { label: "3Y", val: getReturn(756) },
    { label: "5Y", val: getReturn(1260) },
  ];

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="font-mono text-sm font-bold text-foreground">₹{currentNav.toFixed(2)}</span>
        <span className={`inline-flex items-center gap-0.5 text-xs font-mono font-semibold ${dayChange >= 0 ? "text-accent" : "text-destructive"}`}>
          {dayChange >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {dayChange >= 0 ? "+" : ""}{dayChange.toFixed(2)}%
        </span>
        <span className="text-[10px] text-muted-foreground">{d[0]?.date}</span>
      </div>
      <div className="flex gap-1.5 flex-wrap">
        {periods.map((p) => (
          <span key={p.label} className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${p.val >= 0 ? "bg-accent/10 text-accent" : "bg-destructive/10 text-destructive"}`}>
            {p.label}: {p.val >= 0 ? "+" : ""}{p.val.toFixed(1)}%
          </span>
        ))}
      </div>
    </div>
  );
};

const Explorer = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAMCs, setSelectedAMCs] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("All Categories");
  const [selectedSubCategory, setSelectedSubCategory] = useState("All Sub-Categories");
  const [selectedType, setSelectedType] = useState("All Types");
  const [selectedScheme, setSelectedScheme] = useState<MFScheme | null>(null);
  const [chartPeriod, setChartPeriod] = useState("1Y");
  const [page, setPage] = useState(0);
  const [compareList, setCompareList] = useState<MFScheme[]>([]);
  const [showCompare, setShowCompare] = useState(false);
  const [showAMCFilter, setShowAMCFilter] = useState(false);
  const [onlyGrowth, setOnlyGrowth] = useState(false);
  const [onlyDirect, setOnlyDirect] = useState(false);
  const PAGE_SIZE = 15;

  const { data: allSchemes, isLoading: schemesLoading } = useQuery({
    queryKey: ["mf-schemes"],
    queryFn: fetchAllSchemes,
    staleTime: 1000 * 60 * 60,
  });

  const { data: schemeDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ["mf-details", selectedScheme?.schemeCode],
    queryFn: () => fetchSchemeDetails(selectedScheme!.schemeCode),
    enabled: !!selectedScheme,
    staleTime: 1000 * 60 * 15,
  });

  const compareQueries = useQuery({
    queryKey: ["mf-compare", compareList.map((c) => c.schemeCode).join(",")],
    queryFn: async () => {
      const results = await Promise.all(compareList.map((s) => fetchSchemeDetails(s.schemeCode)));
      return results;
    },
    enabled: showCompare && compareList.length >= 2,
    staleTime: 1000 * 60 * 15,
  });

  const toggleCompare = useCallback((scheme: MFScheme) => {
    setCompareList((prev) => {
      const exists = prev.find((s) => s.schemeCode === scheme.schemeCode);
      if (exists) return prev.filter((s) => s.schemeCode !== scheme.schemeCode);
      if (prev.length >= 4) return prev;
      return [...prev, scheme];
    });
  }, []);

  const toggleAMC = useCallback((amc: string) => {
    setSelectedAMCs((prev) => {
      if (prev.includes(amc)) return prev.filter((a) => a !== amc);
      return [...prev, amc];
    });
  }, []);

  useEffect(() => { setPage(0); }, [searchQuery, selectedAMCs, selectedCategory, selectedSubCategory, selectedType, onlyGrowth, onlyDirect]);

  const filteredSchemes = useMemo(() => {
    if (!allSchemes) return [];
    return allSchemes.filter((s) => {
      const amc = guessAMC(s.schemeName);
      if (amc === "Other") return false;
      const lower = s.schemeName.toLowerCase();
      const matchSearch = !searchQuery || lower.includes(searchQuery.toLowerCase());
      const matchAMC = selectedAMCs.length === 0 || selectedAMCs.includes(amc);
      const matchCategory = selectedCategory === "All Categories" || guessCategory(s.schemeName) === selectedCategory;
      const matchSubCat = selectedSubCategory === "All Sub-Categories" || guessSubCategory(s.schemeName) === selectedSubCategory;
      const matchType = selectedType === "All Types" || guessSchemeType(s.schemeName) === selectedType;
      const matchGrowth = !onlyGrowth || lower.includes("growth");
      const matchDirect = !onlyDirect || lower.includes("direct");
      return matchSearch && matchAMC && matchCategory && matchSubCat && matchType && matchGrowth && matchDirect;
    });
  }, [allSchemes, searchQuery, selectedAMCs, selectedCategory, selectedSubCategory, selectedType, onlyGrowth, onlyDirect]);

  const paginatedSchemes = useMemo(() => {
    return filteredSchemes.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  }, [filteredSchemes, page]);

  // Chart data
  const chartData = useMemo(() => {
    if (!schemeDetails?.data?.length) return [];
    const period = CHART_PERIODS.find((p) => p.label === chartPeriod);
    let navData = [...schemeDetails.data].reverse();
    if (period && period.days > 0) {
      navData = navData.slice(-period.days);
    }
    return navData.map((d) => ({ date: d.date, nav: parseFloat(d.nav) }));
  }, [schemeDetails, chartPeriod]);

  // Performance metrics
  const performance = useMemo(() => {
    if (!schemeDetails?.data?.length) return null;
    const data = schemeDetails.data;
    const currentNav = parseFloat(data[0].nav);
    const getReturn = (daysAgo: number) => {
      const target = data.find((_, i) => i >= daysAgo) || data[data.length - 1];
      const oldNav = parseFloat(target.nav);
      return oldNav > 0 ? ((currentNav - oldNav) / oldNav) * 100 : 0;
    };
    return {
      currentNav,
      return1M: getReturn(22), return3M: getReturn(66), return6M: getReturn(132),
      return1Y: getReturn(252), return3Y: getReturn(756), return5Y: getReturn(1260),
    };
  }, [schemeDetails]);

  const ReturnBadge = ({ value, label }: { value: number; label: string }) => (
    <div className="text-center">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <Badge variant={value >= 0 ? "default" : "destructive"} className="font-mono text-sm">
        {value >= 0 ? "+" : ""}{value.toFixed(2)}%
      </Badge>
    </div>
  );

  // Fund detail view
  if (selectedScheme) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-20 pb-12 px-4 max-w-7xl mx-auto">
          <Button variant="ghost" className="mb-4 gap-2" onClick={() => setSelectedScheme(null)}>
            <ArrowLeft className="w-4 h-4" /> Back to Explorer
          </Button>

          {detailsLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-3/4" />
              <Skeleton className="h-6 w-1/2" />
              <Skeleton className="h-[400px] w-full" />
            </div>
          ) : schemeDetails ? (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-foreground leading-tight">
                  {schemeDetails.meta.scheme_name}
                </h1>
                <div className="flex flex-wrap gap-2 mt-3">
                  <Badge variant="secondary">{schemeDetails.meta.fund_house}</Badge>
                  <Badge variant="outline">{schemeDetails.meta.scheme_type}</Badge>
                  <Badge variant="outline">{schemeDetails.meta.scheme_category}</Badge>
                </div>
              </div>

              {performance && (
                <Card>
                  <CardContent className="pt-6">
                    <div className="flex flex-col md:flex-row md:items-center gap-6">
                      <div className="flex items-center gap-2">
                        <IndianRupee className="w-6 h-6 text-primary" />
                        <div>
                          <p className="text-xs text-muted-foreground">Current NAV</p>
                          <p className="text-3xl font-bold text-foreground font-mono">₹{performance.currentNav.toFixed(2)}</p>
                          <p className="text-xs text-muted-foreground flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {schemeDetails.data[0]?.date}
                          </p>
                        </div>
                      </div>
                      <div className="flex-1 grid grid-cols-3 md:grid-cols-6 gap-3">
                        <ReturnBadge value={performance.return1M} label="1M" />
                        <ReturnBadge value={performance.return3M} label="3M" />
                        <ReturnBadge value={performance.return6M} label="6M" />
                        <ReturnBadge value={performance.return1Y} label="1Y" />
                        <ReturnBadge value={performance.return3Y} label="3Y" />
                        <ReturnBadge value={performance.return5Y} label="5Y" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <BarChart3 className="w-5 h-5 text-primary" /> NAV Performance
                    </CardTitle>
                    <div className="flex gap-1">
                      {CHART_PERIODS.map((p) => (
                        <Button key={p.label} size="sm" variant={chartPeriod === p.label ? "default" : "outline"} className="h-7 px-2.5 text-xs" onClick={() => setChartPeriod(p.label)}>
                          {p.label}
                        </Button>
                      ))}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={380}>
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(215, 80%, 28%)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(215, 80%, 28%)" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 13%, 88%)" />
                        <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => { const p = v.split("-"); return `${p[1]}-${p[2]}`; }} interval="preserveStartEnd" minTickGap={50} />
                        <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
                        <Tooltip contentStyle={{ backgroundColor: "hsl(0, 0%, 100%)", border: "1px solid hsl(220, 13%, 88%)", borderRadius: "8px", fontSize: "12px" }} formatter={(value: number) => [`₹${value.toFixed(2)}`, "NAV"]} />
                        <Area type="monotone" dataKey="nav" stroke="hsl(215, 80%, 28%)" strokeWidth={2} fill="url(#navGradient)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-center text-muted-foreground py-12">No data available for this period.</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Info className="w-5 h-5 text-primary" /> Fund Information
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableBody>
                      <TableRow><TableCell className="font-medium text-muted-foreground">Fund House</TableCell><TableCell>{schemeDetails.meta.fund_house}</TableCell></TableRow>
                      <TableRow><TableCell className="font-medium text-muted-foreground">Scheme Type</TableCell><TableCell>{schemeDetails.meta.scheme_type}</TableCell></TableRow>
                      <TableRow><TableCell className="font-medium text-muted-foreground">Category</TableCell><TableCell>{schemeDetails.meta.scheme_category}</TableCell></TableRow>
                      <TableRow><TableCell className="font-medium text-muted-foreground">Scheme Code</TableCell><TableCell className="font-mono">{schemeDetails.meta.scheme_code}</TableCell></TableRow>
                      <TableRow><TableCell className="font-medium text-muted-foreground">Total NAV Records</TableCell><TableCell className="font-mono">{schemeDetails.data.length}</TableCell></TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Recent NAV History</CardTitle>
                  <CardDescription>Last 15 trading days</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead className="text-right">NAV (₹)</TableHead>
                        <TableHead className="text-right">Change</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {schemeDetails.data.slice(0, 15).map((d, i) => {
                        const current = parseFloat(d.nav);
                        const prev = i + 1 < schemeDetails.data.length ? parseFloat(schemeDetails.data[i + 1].nav) : current;
                        const change = current - prev;
                        const changePct = prev > 0 ? (change / prev) * 100 : 0;
                        return (
                          <TableRow key={d.date}>
                            <TableCell>{d.date}</TableCell>
                            <TableCell className="text-right font-mono">₹{current.toFixed(4)}</TableCell>
                            <TableCell className="text-right">
                              <span className={`inline-flex items-center gap-1 font-mono text-sm ${change >= 0 ? "text-accent" : "text-destructive"}`}>
                                {change >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
                              </span>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-12">Could not load fund details.</p>
          )}
        </main>
      </div>
    );
  }

  // Compare view
  if (showCompare && compareList.length >= 2) {
    const compareData = compareQueries.data;
    const getPerf = (data: SchemeDetails["data"], daysAgo: number) => {
      if (!data?.length) return 0;
      const curr = parseFloat(data[0].nav);
      const target = data.find((_, i) => i >= daysAgo) || data[data.length - 1];
      const old = parseFloat(target.nav);
      return old > 0 ? ((curr - old) / old) * 100 : 0;
    };

    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-20 pb-12 px-4 max-w-7xl mx-auto">
          <Button variant="ghost" className="mb-4 gap-2" onClick={() => setShowCompare(false)}>
            <ArrowLeft className="w-4 h-4" /> Back to Explorer
          </Button>
          <h1 className="text-2xl font-bold text-foreground mb-6">Fund Comparison</h1>

          {compareQueries.isLoading ? (
            <Skeleton className="h-[400px] w-full" />
          ) : compareData ? (
            <div className="space-y-6">
              <Card>
                <CardContent className="pt-6 overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="min-w-[200px]">Fund</TableHead>
                        <TableHead className="text-right">NAV</TableHead>
                        <TableHead className="text-right">1M</TableHead>
                        <TableHead className="text-right">3M</TableHead>
                        <TableHead className="text-right">1Y</TableHead>
                        <TableHead className="text-right">3Y</TableHead>
                        <TableHead className="text-right">5Y</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {compareData.map((sd, i) => (
                        <TableRow key={sd.meta.scheme_code}>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: COMPARE_COLORS[i] }} />
                              <span className="font-medium text-sm truncate max-w-[250px]">{sd.meta.scheme_name}</span>
                            </div>
                          </TableCell>
                          <TableCell className="text-right font-mono">₹{parseFloat(sd.data[0]?.nav || "0").toFixed(2)}</TableCell>
                          {[22, 66, 252, 756, 1260].map((d) => {
                            const ret = getPerf(sd.data, d);
                            return (
                              <TableCell key={d} className={`text-right font-mono text-sm ${ret >= 0 ? "text-accent" : "text-destructive"}`}>
                                {ret >= 0 ? "+" : ""}{ret.toFixed(2)}%
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">1-Year NAV Performance (Normalized to 100)</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 13%, 88%)" />
                      <XAxis dataKey="date" type="category" allowDuplicatedCategory={false} tick={{ fontSize: 11 }} tickFormatter={(v) => { const p = v.split("-"); return `${p[1]}-${p[2]}`; }} interval="preserveStartEnd" minTickGap={60} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      {compareData.map((sd, i) => {
                        const navData = [...sd.data].reverse().slice(-252);
                        const baseNav = navData.length > 0 ? parseFloat(navData[0].nav) : 1;
                        const normalized = navData.map((d) => ({
                          date: d.date,
                          [sd.meta.scheme_name.substring(0, 30)]: parseFloat(((parseFloat(d.nav) / baseNav) * 100).toFixed(2)),
                        }));
                        return (
                          <Line key={sd.meta.scheme_code} data={normalized} dataKey={sd.meta.scheme_name.substring(0, 30)} stroke={COMPARE_COLORS[i]} strokeWidth={2} dot={false} name={sd.meta.scheme_name.substring(0, 30)} />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          ) : null}
        </main>
      </div>
    );
  }

  // Main explorer view
  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="absolute top-20 right-0 w-[300px] h-[300px] bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-40 left-0 w-[250px] h-[250px] bg-secondary/5 rounded-full blur-3xl" />
      <Navbar />
      <main className="pt-20 pb-12 px-4 max-w-7xl mx-auto relative">
        <div className="mb-8 animate-fade-up">
          <div className="inline-flex items-center gap-2 gradient-primary text-white px-4 py-2 rounded-full text-sm font-medium mb-4 shadow-lg">
            <Search className="w-4 h-4" /> Explore Funds
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground">Mutual Fund <span className="gradient-text">Explorer</span></h1>
          <p className="text-muted-foreground mt-2">
            Browse mutual fund schemes from our {PARTNER_AMCS.length} partnered AMCs. View NAV, performance, and fund details.
          </p>
        </div>

        {/* Compare bar */}
        {compareList.length > 0 && (
          <Card className="mb-4 border-primary/30 bg-primary/5">
            <CardContent className="py-3 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <GitCompareArrows className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium text-foreground">Compare ({compareList.length}/4):</span>
                {compareList.map((s) => (
                  <Badge key={s.schemeCode} variant="secondary" className="gap-1">
                    {s.schemeName.substring(0, 25)}...
                    <X className="w-3 h-3 cursor-pointer" onClick={() => toggleCompare(s)} />
                  </Badge>
                ))}
              </div>
              <Button size="sm" disabled={compareList.length < 2} onClick={() => setShowCompare(true)} className="gap-1">
                <GitCompareArrows className="w-4 h-4" /> Compare Now
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Filters */}
        <Card className="mb-6">
          <CardContent className="pt-6 space-y-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search mutual funds by name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Row of dropdowns */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger><SelectValue placeholder="Category" /></SelectTrigger>
                <SelectContent>
                  {SCHEME_CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={selectedSubCategory} onValueChange={setSelectedSubCategory}>
                <SelectTrigger><SelectValue placeholder="Sub-Category" /></SelectTrigger>
                <SelectContent>
                  {SUB_CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger><SelectValue placeholder="Scheme Type" /></SelectTrigger>
                <SelectContent>
                  {SCHEME_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <Checkbox checked={onlyGrowth} onCheckedChange={(v) => setOnlyGrowth(!!v)} />
                  Growth Only
                </label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <Checkbox checked={onlyDirect} onCheckedChange={(v) => setOnlyDirect(!!v)} />
                  Direct Only
                </label>
              </div>
            </div>

            {/* Multi-AMC selector */}
            <div>
              <Button variant="outline" size="sm" className="gap-2 mb-2" onClick={() => setShowAMCFilter(!showAMCFilter)}>
                <Filter className="w-4 h-4" />
                {selectedAMCs.length > 0 ? `${selectedAMCs.length} AMC${selectedAMCs.length > 1 ? "s" : ""} selected` : "Filter by AMC"}
                {showAMCFilter ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </Button>
              {selectedAMCs.length > 0 && (
                <Button variant="ghost" size="sm" className="text-xs text-muted-foreground ml-2" onClick={() => setSelectedAMCs([])}>
                  Clear all
                </Button>
              )}
              {showAMCFilter && (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 mt-2 p-3 bg-muted/30 rounded-lg border border-border">
                  {PARTNER_AMCS.map((amc) => (
                    <label key={amc} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-muted/50 p-1.5 rounded">
                      <Checkbox checked={selectedAMCs.includes(amc)} onCheckedChange={() => toggleAMC(amc)} />
                      <span className="truncate">{amc}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* Active filter badges */}
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="secondary" className="text-sm">
                {filteredSchemes.length.toLocaleString()} schemes found
              </Badge>
              {selectedAMCs.map((amc) => (
                <Badge key={amc} variant="outline" className="gap-1 text-xs">
                  {amc}
                  <X className="w-3 h-3 cursor-pointer" onClick={() => toggleAMC(amc)} />
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        {schemesLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full rounded-lg" />
            ))}
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {paginatedSchemes.map((scheme) => {
                const isInCompare = compareList.some((s) => s.schemeCode === scheme.schemeCode);
                return (
                  <Card
                    key={scheme.schemeCode}
                    className={`hover:border-primary/40 transition-all hover:shadow-md ${isInCompare ? "border-primary/40 bg-primary/5" : ""}`}
                  >
                    <CardContent className="py-4 flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        <Checkbox
                          checked={isInCompare}
                          onCheckedChange={() => toggleCompare(scheme)}
                          className="shrink-0 mt-1"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-foreground truncate cursor-pointer hover:text-primary transition-colors" onClick={() => setSelectedScheme(scheme)}>
                            {scheme.schemeName}
                          </p>
                          <div className="flex gap-2 mt-1 mb-2">
                            <Badge variant="outline" className="text-[10px]">{guessAMC(scheme.schemeName)}</Badge>
                            <Badge variant="outline" className="text-[10px]">{guessCategory(scheme.schemeName)}</Badge>
                            {guessSubCategory(scheme.schemeName) && (
                              <Badge variant="outline" className="text-[10px]">{guessSubCategory(scheme.schemeName)}</Badge>
                            )}
                          </div>
                          <FundCardPerf schemeCode={scheme.schemeCode} />
                        </div>
                      </div>
                      <Button size="sm" variant="ghost" className="text-primary shrink-0" onClick={() => setSelectedScheme(scheme)}>
                        Details →
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {filteredSchemes.length > PAGE_SIZE && (
              <div className="flex items-center justify-center gap-4 mt-8">
                <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground">
                  Page {page + 1} of {Math.ceil(filteredSchemes.length / PAGE_SIZE)}
                </span>
                <Button variant="outline" size="sm" disabled={(page + 1) * PAGE_SIZE >= filteredSchemes.length} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            )}

            {paginatedSchemes.length === 0 && !schemesLoading && (
              <div className="text-center py-16">
                <Search className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-foreground">No schemes found</h3>
                <p className="text-muted-foreground mt-1">Try adjusting your search or filters.</p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
};

export default Explorer;
