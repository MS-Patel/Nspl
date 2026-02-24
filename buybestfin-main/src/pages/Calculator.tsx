import { useState, useMemo } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { Calculator as CalcIcon, TrendingUp, IndianRupee, Target } from "lucide-react";

const formatCurrency = (value: number) => {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)} L`;
  return `₹${value.toLocaleString("en-IN")}`;
};

const SIPCalculator = () => {
  const [monthlyInvestment, setMonthlyInvestment] = useState(5000);
  const [years, setYears] = useState(10);
  const [expectedReturn, setExpectedReturn] = useState(12);

  const result = useMemo(() => {
    const months = years * 12;
    const monthlyRate = expectedReturn / 12 / 100;
    const totalInvested = monthlyInvestment * months;
    const futureValue = monthlyInvestment * ((Math.pow(1 + monthlyRate, months) - 1) / monthlyRate) * (1 + monthlyRate);
    const wealthGained = futureValue - totalInvested;

    const yearlyData = [];
    for (let y = 1; y <= years; y++) {
      const m = y * 12;
      const inv = monthlyInvestment * m;
      const fv = monthlyInvestment * ((Math.pow(1 + monthlyRate, m) - 1) / monthlyRate) * (1 + monthlyRate);
      yearlyData.push({ year: `${y}Y`, invested: Math.round(inv), value: Math.round(fv) });
    }

    return { totalInvested, futureValue: Math.round(futureValue), wealthGained: Math.round(wealthGained), yearlyData };
  }, [monthlyInvestment, years, expectedReturn]);

  const pieData = [
    { name: "Invested", value: result.totalInvested },
    { name: "Returns", value: result.wealthGained },
  ];

  return (
    <div className="space-y-8">
      <div className="space-y-6">
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>Monthly Investment</label>
            <span className="text-sm font-bold text-primary">{formatCurrency(monthlyInvestment)}</span>
          </div>
          <Slider value={[monthlyInvestment]} onValueChange={([v]) => setMonthlyInvestment(v)} min={500} max={100000} step={500} />
        </div>
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>Investment Period</label>
            <span className="text-sm font-bold text-primary">{years} Years</span>
          </div>
          <Slider value={[years]} onValueChange={([v]) => setYears(v)} min={1} max={30} step={1} />
        </div>
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>Expected Return (p.a.)</label>
            <span className="text-sm font-bold text-primary">{expectedReturn}%</span>
          </div>
          <Slider value={[expectedReturn]} onValueChange={([v]) => setExpectedReturn(v)} min={1} max={30} step={0.5} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Invested", value: result.totalInvested, icon: IndianRupee },
          { label: "Est. Returns", value: result.wealthGained, icon: TrendingUp },
          { label: "Total Value", value: result.futureValue, icon: Target },
        ].map((item) => (
          <div key={item.label} className="bg-muted/50 rounded-xl p-4 text-center">
            <item.icon className="w-5 h-5 text-primary mx-auto mb-1" />
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="text-sm font-bold text-foreground">{formatCurrency(item.value)}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="flex items-center justify-center">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" stroke="none">
                <Cell fill="hsl(215, 80%, 28%)" />
                <Cell fill="hsl(160, 50%, 40%)" />
              </Pie>
              <Tooltip formatter={(value: number) => formatCurrency(value)} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={result.yearlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 13%, 88%)" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} stroke="hsl(220, 10%, 46%)" />
              <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 10 }} stroke="hsl(220, 10%, 46%)" width={70} />
              <Tooltip formatter={(value: number) => formatCurrency(value)} />
              <Area type="monotone" dataKey="invested" stackId="1" stroke="hsl(215, 80%, 28%)" fill="hsl(215, 80%, 28%)" fillOpacity={0.3} name="Invested" />
              <Area type="monotone" dataKey="value" stackId="2" stroke="hsl(160, 50%, 40%)" fill="hsl(160, 50%, 40%)" fillOpacity={0.3} name="Total Value" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

const LumpsumCalculator = () => {
  const [investment, setInvestment] = useState(100000);
  const [years, setYears] = useState(10);
  const [expectedReturn, setExpectedReturn] = useState(12);

  const result = useMemo(() => {
    const futureValue = investment * Math.pow(1 + expectedReturn / 100, years);
    const wealthGained = futureValue - investment;

    const yearlyData = [];
    for (let y = 1; y <= years; y++) {
      const fv = investment * Math.pow(1 + expectedReturn / 100, y);
      yearlyData.push({ year: `${y}Y`, invested: investment, value: Math.round(fv) });
    }

    return { totalInvested: investment, futureValue: Math.round(futureValue), wealthGained: Math.round(wealthGained), yearlyData };
  }, [investment, years, expectedReturn]);

  const pieData = [
    { name: "Invested", value: result.totalInvested },
    { name: "Returns", value: result.wealthGained },
  ];

  return (
    <div className="space-y-8">
      <div className="space-y-6">
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>One-Time Investment</label>
            <span className="text-sm font-bold text-primary">{formatCurrency(investment)}</span>
          </div>
          <Slider value={[investment]} onValueChange={([v]) => setInvestment(v)} min={5000} max={10000000} step={5000} />
        </div>
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>Investment Period</label>
            <span className="text-sm font-bold text-primary">{years} Years</span>
          </div>
          <Slider value={[years]} onValueChange={([v]) => setYears(v)} min={1} max={30} step={1} />
        </div>
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>Expected Return (p.a.)</label>
            <span className="text-sm font-bold text-primary">{expectedReturn}%</span>
          </div>
          <Slider value={[expectedReturn]} onValueChange={([v]) => setExpectedReturn(v)} min={1} max={30} step={0.5} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Invested", value: result.totalInvested, icon: IndianRupee },
          { label: "Est. Returns", value: result.wealthGained, icon: TrendingUp },
          { label: "Total Value", value: result.futureValue, icon: Target },
        ].map((item) => (
          <div key={item.label} className="bg-muted/50 rounded-xl p-4 text-center">
            <item.icon className="w-5 h-5 text-primary mx-auto mb-1" />
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="text-sm font-bold text-foreground">{formatCurrency(item.value)}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="flex items-center justify-center">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" stroke="none">
                <Cell fill="hsl(215, 80%, 28%)" />
                <Cell fill="hsl(160, 50%, 40%)" />
              </Pie>
              <Tooltip formatter={(value: number) => formatCurrency(value)} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={result.yearlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 13%, 88%)" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} stroke="hsl(220, 10%, 46%)" />
              <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 10 }} stroke="hsl(220, 10%, 46%)" width={70} />
              <Tooltip formatter={(value: number) => formatCurrency(value)} />
              <Area type="monotone" dataKey="invested" stroke="hsl(215, 80%, 28%)" fill="hsl(215, 80%, 28%)" fillOpacity={0.3} name="Invested" />
              <Area type="monotone" dataKey="value" stroke="hsl(160, 50%, 40%)" fill="hsl(160, 50%, 40%)" fillOpacity={0.3} name="Total Value" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

const CalculatorPage = () => {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="absolute top-20 right-0 w-[300px] h-[300px] bg-secondary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-20 left-0 w-[250px] h-[250px] bg-primary/5 rounded-full blur-3xl" />
      <Navbar />
      <main className="pt-24 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Hero */}
          <div className="text-center mb-12 animate-fade-up">
            <div className="inline-flex items-center gap-2 gradient-primary text-white px-4 py-2 rounded-full text-sm font-medium mb-4 shadow-lg">
              <CalcIcon className="w-4 h-4" />
              SIP Calculator
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
              Plan Your <span className="gradient-text">Financial Future</span>
            </h1>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Use our calculators to estimate your investment growth. See how SIP or Lumpsum investments compound over time.
            </p>
          </div>

          {/* Calculator */}
          <Card className="max-w-4xl mx-auto border-border/50 shadow-2xl animate-fade-up" style={{ animationDelay: '0.1s' }}>
            <CardHeader>
              <Tabs defaultValue="sip" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-6">
                  <TabsTrigger value="sip" className="text-sm font-semibold" style={{ fontFamily: "DM Sans" }}>
                    SIP Calculator
                  </TabsTrigger>
                  <TabsTrigger value="lumpsum" className="text-sm font-semibold" style={{ fontFamily: "DM Sans" }}>
                    Lumpsum Calculator
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="sip">
                  <SIPCalculator />
                </TabsContent>
                <TabsContent value="lumpsum">
                  <LumpsumCalculator />
                </TabsContent>
              </Tabs>
            </CardHeader>
          </Card>

          {/* Info cards */}
          <div className="grid sm:grid-cols-3 gap-6 mt-16 max-w-4xl mx-auto">
            {[
              { title: "Power of Compounding", desc: "Your returns earn returns. Starting early with even ₹500/month can create significant wealth over 20+ years." },
              { title: "SIP vs Lumpsum", desc: "SIP averages out market volatility (rupee cost averaging), while lumpsum works better in rising markets." },
              { title: "Tax Benefits", desc: "ELSS mutual funds offer tax deduction up to ₹1.5L under Section 80C with just 3 years lock-in." },
            ].map((item) => (
              <Card key={item.title} className="border-border hover:shadow-lg transition-shadow">
                <CardContent className="pt-6">
                  <h3 className="font-bold text-foreground mb-2" style={{ fontFamily: "DM Sans" }}>{item.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
};

export default CalculatorPage;
