import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Info, BarChart3, Calendar, ExternalLink } from "lucide-react";
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";

interface UnlistedStock {
  name: string;
  sector: string;
  lotSize: number;
  ipoExpected: string;
  description: string;
  highlights: string[];
  financials: { year: string; revenue: number; profit: number }[];
}

const unlistedStocks: UnlistedStock[] = [
  {
    name: "Swiggy (Pre-IPO)",
    sector: "Food Tech",
    lotSize: 25,
    ipoExpected: "Listed — Nov 2024",
    description: "India's leading food delivery and quick commerce platform operating Swiggy Instamart. Competes with Zomato in the food-tech space.",
    highlights: ["40%+ market share in food delivery", "Instamart rapid growth", "Strong brand recognition", "Expanding into quick commerce"],
    financials: [
      { year: "FY21", revenue: 2500, profit: -2100 }, { year: "FY22", revenue: 5100, profit: -3600 },
      { year: "FY23", revenue: 8300, profit: -2500 }, { year: "FY24", revenue: 11200, profit: -920 },
    ],
  },
  {
    name: "OYO Rooms",
    sector: "Hospitality",
    lotSize: 100,
    ipoExpected: "2025 (Expected)",
    description: "Global hospitality chain operating budget hotels, premium stays, and vacation homes across 35+ countries.",
    highlights: ["World's 3rd largest hotel chain", "Asset-light model", "Path to profitability", "Global presence"],
    financials: [
      { year: "FY21", revenue: 800, profit: -2400 }, { year: "FY22", revenue: 1800, profit: -1800 },
      { year: "FY23", revenue: 5200, profit: -800 }, { year: "FY24", revenue: 6100, profit: 200 },
    ],
  },
  {
    name: "NSDL (National Securities Depository)",
    sector: "Financial Services",
    lotSize: 10,
    ipoExpected: "2025 (Expected)",
    description: "India's first and largest depository handling demat accounts for millions of investors. Critical market infrastructure.",
    highlights: ["Monopoly-like position", "Consistent profitability", "High entry barriers", "Regulatory moat"],
    financials: [
      { year: "FY21", revenue: 750, profit: 310 }, { year: "FY22", revenue: 1050, profit: 480 },
      { year: "FY23", revenue: 1300, profit: 560 }, { year: "FY24", revenue: 1600, profit: 720 },
    ],
  },
  {
    name: "boAt Lifestyle",
    sector: "Consumer Electronics",
    lotSize: 100,
    ipoExpected: "2025 (Expected)",
    description: "India's #1 earwear brand and top 5 globally. Premium audio products, smartwatches, and lifestyle accessories.",
    highlights: ["#1 TWS brand in India", "Strong D2C presence", "Celebrity partnerships", "Fast revenue growth"],
    financials: [
      { year: "FY21", revenue: 1500, profit: 80 }, { year: "FY22", revenue: 2800, profit: 150 },
      { year: "FY23", revenue: 3200, profit: -60 }, { year: "FY24", revenue: 3500, profit: 120 },
    ],
  },
  {
    name: "PhonePe",
    sector: "Fintech",
    lotSize: 15,
    ipoExpected: "2026 (Expected)",
    description: "India's largest UPI payments platform with 500M+ registered users. Expanding into insurance, lending, and investments.",
    highlights: ["#1 UPI market share", "500M+ users", "Insurance & lending expansion", "Walmart-backed"],
    financials: [
      { year: "FY21", revenue: 800, profit: -1700 }, { year: "FY22", revenue: 1900, profit: -2100 },
      { year: "FY23", revenue: 3200, profit: -1700 }, { year: "FY24", revenue: 5100, profit: -800 },
    ],
  },
  {
    name: "Chennai Super Kings (CSK)",
    sector: "Sports / Entertainment",
    lotSize: 50,
    ipoExpected: "N/A",
    description: "One of the most successful IPL franchises with massive brand value, led by MS Dhoni. Revenue from broadcasting, sponsorships & merchandise.",
    highlights: ["5x IPL Champions", "Massive brand value", "Strong fanbase", "Consistent revenue"],
    financials: [
      { year: "FY21", revenue: 380, profit: 120 }, { year: "FY22", revenue: 480, profit: 150 },
      { year: "FY23", revenue: 560, profit: 190 }, { year: "FY24", revenue: 650, profit: 220 },
    ],
  },
];

const StockCard = ({ stock, onSelect, isSelected }: { stock: UnlistedStock; onSelect: () => void; isSelected: boolean }) => {
  return (
    <Card
      className={`cursor-pointer transition-all duration-300 hover:shadow-lg border-2 ${isSelected ? "border-primary shadow-lg" : "border-transparent"}`}
      onClick={onSelect}
    >
      <CardContent className="p-4">
        <div className="flex justify-between items-start mb-2">
          <div>
            <h3 className="font-bold text-sm font-sans">{stock.name}</h3>
            <Badge variant="secondary" className="text-[10px] mt-1">{stock.sector}</Badge>
          </div>
          <Badge variant="outline" className="text-[10px]">{stock.ipoExpected}</Badge>
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground mt-2">
          <span>Lot: {stock.lotSize} shares</span>
          <span>Contact for price</span>
        </div>
      </CardContent>
    </Card>
  );
};

const UnlistedEquities = () => {
  const [selected, setSelected] = useState(0);
  const stock = unlistedStocks[selected];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-24 pb-16 px-4 max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10 animate-fade-up">
          <h1 className="text-4xl md:text-5xl font-bold mb-3">
            <span className="gradient-text">Unlisted Equities</span>
          </h1>
          <p className="text-muted-foreground max-w-xl mx-auto">Pre-IPO investment opportunities in India's fastest-growing companies. Contact us for latest quotes.</p>
        </div>

        {/* Disclaimer */}
        <div className="glass-card rounded-xl p-4 mb-8 flex items-start gap-3 animate-fade-up">
          <Info className="w-5 h-5 text-primary mt-0.5 shrink-0" />
          <p className="text-xs text-muted-foreground">
            Unlisted shares carry higher risk. Past performance is not indicative of future results. Contact us on WhatsApp for actual buy/sell quotes and latest pricing.
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Stock List */}
          <div className="lg:col-span-1 space-y-3">
            <h2 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">Available Stocks</h2>
            {unlistedStocks.map((s, i) => (
              <StockCard key={s.name} stock={s} onSelect={() => setSelected(i)} isSelected={selected === i} />
            ))}
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-2 space-y-6 animate-fade-up">
            {/* Info Header */}
            <Card>
              <CardContent className="p-6">
                <div className="flex flex-wrap justify-between items-start gap-4">
                  <div>
                    <h2 className="text-2xl font-bold font-sans">{stock.name}</h2>
                    <div className="flex items-center gap-3 mt-1">
                      <Badge variant="secondary">{stock.sector}</Badge>
                      <span className="text-xs text-muted-foreground flex items-center gap-1"><Calendar className="w-3 h-3" /> IPO: {stock.ipoExpected}</span>
                    </div>
                  </div>
                  <a href="https://wa.me/917265098822?text=Hi%2C%20I%20want%20the%20latest%20price%20for%20unlisted%20shares" target="_blank" rel="noopener noreferrer">
                    <Button size="sm" className="gradient-primary text-white">
                      Get Latest Price <ExternalLink className="w-3 h-3 ml-1" />
                    </Button>
                  </a>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-5 pt-4 border-t border-border">
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">Lot Size</p>
                    <p className="font-bold font-sans">{stock.lotSize} shares</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">Pricing</p>
                    <p className="font-bold font-sans text-primary">Contact for Quote</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Tabs */}
            <Tabs defaultValue="financials">
              <TabsList className="w-full">
                <TabsTrigger value="financials" className="flex-1">Financials</TabsTrigger>
                <TabsTrigger value="about" className="flex-1">About</TabsTrigger>
              </TabsList>

              <TabsContent value="financials">
                <Card>
                  <CardContent className="p-4 pt-6">
                    <p className="text-sm font-medium mb-3">Revenue & Profit (₹ Cr)</p>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={stock.financials}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(200,13%,88%)" />
                        <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip formatter={(v: number) => [`₹${v} Cr`]} />
                        <Bar dataKey="revenue" fill="hsl(207,72%,38%)" radius={[4, 4, 0, 0]} name="Revenue" />
                        <Bar dataKey="profit" fill="hsl(90,67%,41%)" radius={[4, 4, 0, 0]} name="Profit" />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="about">
                <Card>
                  <CardContent className="p-6 space-y-4">
                    <p className="text-sm text-muted-foreground">{stock.description}</p>
                    <div>
                      <p className="text-sm font-bold mb-2">Key Highlights</p>
                      <div className="grid sm:grid-cols-2 gap-2">
                        {stock.highlights.map((h) => (
                          <div key={h} className="flex items-center gap-2 text-sm">
                            <span className="w-2 h-2 rounded-full gradient-primary shrink-0" />
                            {h}
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>

            {/* CTA */}
            <Card className="gradient-primary text-white">
              <CardContent className="p-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold font-sans">Interested in {stock.name}?</h3>
                  <p className="text-sm opacity-90">Get the best quote and complete guidance on WhatsApp.</p>
                </div>
                <a href="https://wa.me/917265098822?text=Hi%2C%20I%20am%20interested%20in%20unlisted%20shares" target="_blank" rel="noopener noreferrer">
                  <Button variant="secondary" className="bg-white text-primary hover:bg-white/90">
                    Chat on WhatsApp <ExternalLink className="w-4 h-4 ml-1" />
                  </Button>
                </a>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default UnlistedEquities;
