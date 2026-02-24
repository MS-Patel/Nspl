import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BookOpen, TrendingUp, Shield, BarChart3, Target, Layers, Globe, Landmark } from "lucide-react";

const FUND_CATEGORIES = [
  {
    tab: "equity",
    label: "Equity",
    icon: TrendingUp,
    funds: [
      {
        name: "Large Cap Funds",
        risk: "Moderate",
        returns: "10–14%",
        horizon: "5+ years",
        desc: "Invest in top 100 companies by market cap (Nifty 100). These are well-established blue-chip companies like Reliance, TCS, HDFC Bank. Relatively stable and suitable for long-term wealth building.",
        who: "Investors seeking steady growth with lower equity risk.",
        examples: "SBI Bluechip, ICICI Pru Bluechip, Axis Bluechip",
      },
      {
        name: "Mid Cap Funds",
        risk: "High",
        returns: "12–18%",
        horizon: "5–7 years",
        desc: "Invest in 101st to 250th companies by market cap. These companies are in a growth phase — larger than small caps but still expanding. Higher return potential with increased volatility.",
        who: "Investors with higher risk tolerance seeking above-average returns.",
        examples: "Kotak Emerging Equity, HDFC Mid-Cap Opportunities, Axis Midcap",
      },
      {
        name: "Small Cap Funds",
        risk: "Very High",
        returns: "15–25%",
        horizon: "7+ years",
        desc: "Invest in companies ranked 251st and below. These can be future mid/large caps. Very high growth potential but also susceptible to sharp drawdowns during market corrections.",
        who: "Aggressive investors with long horizons who can stomach 30–50% drops.",
        examples: "SBI Small Cap, Nippon Small Cap, Quant Small Cap",
      },
      {
        name: "Flexi Cap Funds",
        risk: "Moderate-High",
        returns: "12–16%",
        horizon: "5+ years",
        desc: "Fund manager freely invests across large, mid, and small caps without any fixed allocation. Offers flexibility to shift between market segments based on opportunities.",
        who: "Investors who want diversified equity exposure with professional flexibility.",
        examples: "Parag Parikh Flexi Cap, HDFC Flexi Cap, UTI Flexi Cap",
      },
      {
        name: "ELSS (Tax Saving)",
        risk: "Moderate-High",
        returns: "12–16%",
        horizon: "3 years (lock-in)",
        desc: "Equity Linked Savings Scheme with shortest lock-in among 80C investments. Invest primarily in equities and qualify for ₹1.5L tax deduction under Section 80C.",
        who: "Taxpayers looking to save tax while building wealth. Shortest lock-in at 3 years.",
        examples: "Mirae Asset Tax Saver, Axis Long Term Equity, Quant ELSS",
      },
      {
        name: "Index Funds / ETFs",
        risk: "Moderate",
        returns: "10–14%",
        horizon: "5+ years",
        desc: "Passively track indices like Nifty 50, Sensex, or Nifty Next 50. Very low expense ratios (0.1–0.3%). No fund manager bias — you get exact market returns.",
        who: "Cost-conscious investors who believe in market returns over active management.",
        examples: "UTI Nifty 50, HDFC Index Sensex, Motilal Oswal Nifty Next 50",
      },
    ],
  },
  {
    tab: "debt",
    label: "Debt",
    icon: Shield,
    funds: [
      {
        name: "Liquid Funds",
        risk: "Very Low",
        returns: "4–6%",
        horizon: "1 day – 3 months",
        desc: "Invest in money market instruments with maturity up to 91 days. Almost zero risk. Better than savings account for parking short-term money. NAV rarely drops.",
        who: "Anyone wanting to park money for days/weeks with near-zero risk.",
        examples: "HDFC Liquid, SBI Liquid, ICICI Pru Liquid",
      },
      {
        name: "Short Duration Funds",
        risk: "Low",
        returns: "6–8%",
        horizon: "1–3 years",
        desc: "Invest in debt instruments with 1–3 year maturity. Moderate interest rate risk. Good alternative to FDs for those in higher tax brackets (with indexation benefit).",
        who: "Conservative investors with 1–3 year goals seeking better-than-FD returns.",
        examples: "HDFC Short Term Debt, Axis Short Duration, ICICI Pru Short Term",
      },
      {
        name: "Gilt Funds",
        risk: "Moderate",
        returns: "6–9%",
        horizon: "3–5 years",
        desc: "Invest exclusively in government securities. Zero credit risk (backed by govt), but interest rate risk exists. Perform very well when RBI cuts rates.",
        who: "Investors seeking zero credit risk willing to accept interest rate volatility.",
        examples: "SBI Magnum Gilt, ICICI Pru Gilt, Nippon Gilt",
      },
      {
        name: "Corporate Bond Funds",
        risk: "Low-Moderate",
        returns: "7–9%",
        horizon: "2–4 years",
        desc: "Invest at least 80% in highest-rated (AA+ and above) corporate bonds. Slightly higher returns than gilt with minimal additional credit risk.",
        who: "Investors comfortable with high-quality corporate exposure for better yields.",
        examples: "HDFC Corporate Bond, ICICI Pru Corporate Bond, Kotak Corporate Bond",
      },
    ],
  },
  {
    tab: "hybrid",
    label: "Hybrid",
    icon: Layers,
    funds: [
      {
        name: "Balanced Advantage Funds (BAF)",
        risk: "Moderate",
        returns: "9–13%",
        horizon: "3–5 years",
        desc: "Dynamically shift between equity and debt based on market valuations. When markets are expensive, equity allocation reduces automatically. Built-in risk management.",
        who: "First-time equity investors or those who want automated asset allocation.",
        examples: "ICICI Pru BAF, HDFC Balanced Advantage, Edelweiss BAF",
      },
      {
        name: "Aggressive Hybrid Funds",
        risk: "Moderate-High",
        returns: "10–14%",
        horizon: "5+ years",
        desc: "Invest 65–80% in equity and 20–35% in debt. Equity taxation applies (since equity > 65%). The debt portion cushions falls while equity drives growth.",
        who: "Investors wanting equity-heavy exposure with some stability.",
        examples: "Canara Robeco Equity Hybrid, SBI Equity Hybrid, Mirae Asset Hybrid",
      },
      {
        name: "Multi Asset Allocation",
        risk: "Moderate",
        returns: "10–14%",
        horizon: "3–5 years",
        desc: "Invest across at least 3 asset classes — equity, debt, and gold/REIT/international. Minimum 10% in each. True diversification across asset classes.",
        who: "Investors wanting one-fund diversification across multiple assets.",
        examples: "ICICI Pru Multi Asset, HDFC Multi Asset, Quant Multi Asset",
      },
    ],
  },
  {
    tab: "others",
    label: "Others",
    icon: Globe,
    funds: [
      {
        name: "Sectoral / Thematic Funds",
        risk: "Very High",
        returns: "Varies widely",
        horizon: "5+ years",
        desc: "Invest in a single sector (IT, Pharma, Banking) or theme (ESG, Manufacturing, Infrastructure). Very concentrated risk — entire portfolio linked to one theme.",
        who: "Experienced investors with strong sector conviction. Not for beginners.",
        examples: "ICICI Pru Technology, SBI PSU, Nippon India Pharma",
      },
      {
        name: "International Funds",
        risk: "High",
        returns: "10–15%",
        horizon: "5+ years",
        desc: "Invest in global companies like Apple, Google, Microsoft via Indian mutual funds. Provides geographical diversification and currency appreciation benefit (USD vs INR).",
        who: "Investors seeking international diversification without foreign brokerage hassle.",
        examples: "Motilal Oswal Nasdaq 100, PGIM India Global Equity, Franklin US Opp",
      },
      {
        name: "Solution Oriented (Retirement/Children)",
        risk: "Varies",
        returns: "10–14%",
        horizon: "5+ years (5 year lock-in)",
        desc: "Goal-specific funds with mandatory 5-year lock-in. Designed for retirement or children's education/marriage. Allocation adjusts as target date approaches.",
        who: "Parents or individuals planning for specific long-term goals.",
        examples: "HDFC Retirement Savings, ICICI Pru Child Care, SBI Retirement Benefit",
      },
    ],
  },
];

const riskColor = (risk: string) => {
  if (risk.includes("Very Low")) return "bg-secondary/20 text-secondary";
  if (risk.includes("Very High")) return "bg-destructive/20 text-destructive";
  if (risk.includes("Low")) return "bg-accent/20 text-accent";
  if (risk.includes("High")) return "bg-primary/20 text-primary";
  return "bg-secondary/20 text-secondary";
};

const FundKnowledge = () => {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="absolute top-20 right-0 w-[300px] h-[300px] bg-accent/5 rounded-full blur-3xl" />
      <div className="absolute bottom-40 left-0 w-[250px] h-[250px] bg-primary/5 rounded-full blur-3xl" />
      <Navbar />
      <main className="pt-24 pb-16 max-w-7xl mx-auto px-4 relative">
        <div className="text-center mb-12 animate-fade-up">
          <div className="inline-flex items-center gap-2 gradient-primary text-white px-4 py-2 rounded-full text-sm font-medium mb-4 shadow-lg">
            <BookOpen className="w-4 h-4" /> Fund Academy
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
            Mutual Fund <span className="gradient-text">Categories</span>
          </h1>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Understand every type of mutual fund — from safe liquid funds to high-growth small caps. Know the risk, expected returns, and who each category is best suited for.
          </p>
        </div>

        <Tabs defaultValue="equity" className="w-full">
          <TabsList className="grid w-full grid-cols-4 max-w-lg mx-auto mb-8">
            {FUND_CATEGORIES.map((cat) => (
              <TabsTrigger key={cat.tab} value={cat.tab} className="gap-1.5 text-sm">
                <cat.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{cat.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {FUND_CATEGORIES.map((cat) => (
            <TabsContent key={cat.tab} value={cat.tab}>
              <div className="grid gap-6">
                {cat.funds.map((fund) => (
                  <Card key={fund.name} className="border-border hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex items-start justify-between flex-wrap gap-3">
                        <CardTitle className="text-xl" style={{ fontFamily: "DM Sans" }}>{fund.name}</CardTitle>
                        <div className="flex gap-2">
                          <Badge className={riskColor(fund.risk)}>{fund.risk} Risk</Badge>
                          <Badge variant="outline" className="font-mono">{fund.returns} p.a.</Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-muted-foreground leading-relaxed">{fund.desc}</p>
                      <div className="grid sm:grid-cols-3 gap-4">
                        <div className="bg-muted/50 rounded-lg p-3">
                          <p className="text-xs text-muted-foreground font-medium mb-1">Ideal Horizon</p>
                          <p className="text-sm font-semibold text-foreground">{fund.horizon}</p>
                        </div>
                        <div className="bg-muted/50 rounded-lg p-3">
                          <p className="text-xs text-muted-foreground font-medium mb-1">Best For</p>
                          <p className="text-sm text-foreground">{fund.who}</p>
                        </div>
                        <div className="bg-muted/50 rounded-lg p-3">
                          <p className="text-xs text-muted-foreground font-medium mb-1">Popular Funds</p>
                          <p className="text-sm text-foreground">{fund.examples}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          ))}
        </Tabs>

        {/* Quick comparison table */}
        <Card className="mt-16 border-border">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary" />
              Quick Risk–Return Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 text-muted-foreground font-medium">Category</th>
                  <th className="text-left py-3 px-2 text-muted-foreground font-medium">Risk</th>
                  <th className="text-left py-3 px-2 text-muted-foreground font-medium">Returns (p.a.)</th>
                  <th className="text-left py-3 px-2 text-muted-foreground font-medium">Min. Horizon</th>
                </tr>
              </thead>
              <tbody>
                {FUND_CATEGORIES.flatMap((cat) =>
                  cat.funds.map((f) => (
                    <tr key={f.name} className="border-b border-border/50 hover:bg-muted/30">
                      <td className="py-2.5 px-2 font-medium text-foreground">{f.name}</td>
                      <td className="py-2.5 px-2"><Badge className={`${riskColor(f.risk)} text-xs`}>{f.risk}</Badge></td>
                      <td className="py-2.5 px-2 font-mono text-foreground">{f.returns}</td>
                      <td className="py-2.5 px-2 text-muted-foreground">{f.horizon}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </main>
      <Footer />
    </div>
  );
};

export default FundKnowledge;
