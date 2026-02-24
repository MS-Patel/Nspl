import { Link } from "react-router-dom";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { TrendingUp, BarChart3, Shield, Landmark, Building2, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const products = [
  {
    icon: TrendingUp,
    title: "Mutual Funds",
    desc: "Diversified portfolio of equity, debt & hybrid funds from 15+ partner AMCs. SIP starting ₹500/month with expert advisory.",
    features: ["SIP & Lumpsum", "Equity / Debt / Hybrid", "Tax-saving ELSS", "NFO Access"],
    link: "/explorer",
    linkText: "Explore Funds",
    color: "from-primary to-accent",
  },
  {
    icon: BarChart3,
    title: "Unlisted Equities",
    desc: "Invest in high-growth pre-IPO companies before they list. Access exclusive unlisted shares at competitive rates.",
    features: ["Pre-IPO Shares", "High Growth Potential", "Portfolio Diversification", "Expert Research"],
    link: "/unlisted-equities",
    linkText: "View Unlisted Stocks",
    color: "from-secondary to-accent",
  },
  {
    icon: Landmark,
    title: "Listed Equities",
    desc: "Trade NSE & BSE listed stocks with live market data, real-time quotes, and comprehensive research tools.",
    features: ["Live NSE/BSE Prices", "Stock Research", "Historical Charts", "Market Indices"],
    link: "/live-market",
    linkText: "Live Market",
    color: "from-primary to-secondary",
  },
  {
    icon: Shield,
    title: "Bonds",
    desc: "Secure fixed-income instruments including Government Bonds, Corporate Bonds & Tax-Free Bonds for stable returns.",
    features: ["Government Bonds", "Corporate Bonds", "Tax-Free Bonds", "Regular Income"],
    link: "/products",
    linkText: "Coming Soon",
    color: "from-accent to-primary",
  },
  {
    icon: Building2,
    title: "Corporate Fixed Deposits",
    desc: "Earn higher interest rates than bank FDs with AAA-rated corporate fixed deposits. Tenure from 1 to 5 years.",
    features: ["Higher Returns", "AAA Rated", "Flexible Tenure", "Monthly Interest Option"],
    link: "/products",
    linkText: "Coming Soon",
    color: "from-secondary to-primary",
  },
];

const Products = () => (
  <div className="min-h-screen bg-background">
    <Navbar />
    <div className="pt-24 pb-16 px-4 max-w-7xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-16 animate-fade-up">
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          Our <span className="gradient-text">Products</span>
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          A complete suite of financial products to help you build wealth, generate income, and achieve your goals.
        </p>
      </div>

      {/* Products Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {products.map((p, i) => (
          <Card
            key={p.title}
            className="group relative overflow-hidden border-border/50 hover:shadow-xl transition-all duration-500 animate-fade-up"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            {/* Top gradient bar */}
            <div className={`h-1.5 w-full bg-gradient-to-r ${p.color}`} />
            <CardContent className="p-6 flex flex-col h-full">
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${p.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                <p.icon className="w-7 h-7 text-primary-foreground" />
              </div>
              <h3 className="text-xl font-bold mb-2 font-sans">{p.title}</h3>
              <p className="text-sm text-muted-foreground mb-4 flex-1">{p.desc}</p>
              <div className="flex flex-wrap gap-2 mb-5">
                {p.features.map((f) => (
                  <span key={f} className="text-xs px-2.5 py-1 rounded-full bg-muted text-muted-foreground">{f}</span>
                ))}
              </div>
              <Link to={p.link}>
                <Button size="sm" variant={p.linkText === "Coming Soon" ? "outline" : "default"} className={p.linkText !== "Coming Soon" ? "gradient-primary border-0 text-white w-full" : "w-full"}>
                  {p.linkText} <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* CTA */}
      <div className="mt-20 text-center glass-card rounded-2xl p-10 animate-fade-up">
        <h2 className="text-2xl font-bold mb-3">Not sure where to start?</h2>
        <p className="text-muted-foreground mb-6 max-w-lg mx-auto">Take our Risk Analyzer quiz to find the right mix of products for your financial goals.</p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link to="/risk-profile"><Button className="gradient-primary border-0 text-white">Take Risk Quiz</Button></Link>
          <Link to="/goal-calculator"><Button variant="outline">Plan a Goal</Button></Link>
        </div>
      </div>
    </div>
    <Footer />
  </div>
);

export default Products;
