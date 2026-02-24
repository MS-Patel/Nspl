import { useState, useMemo } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { Target, TrendingUp, IndianRupee, ArrowUpRight, ArrowDownRight, Layers } from "lucide-react";

const fmt = (v: number) => {
  if (v >= 10000000) return `₹${(v / 10000000).toFixed(2)} Cr`;
  if (v >= 100000) return `₹${(v / 100000).toFixed(2)} L`;
  return `₹${v.toLocaleString("en-IN")}`;
};

const COLORS = ["hsl(215, 80%, 28%)", "hsl(160, 50%, 40%)", "hsl(38, 92%, 50%)"];

// Step-up SIP Calculator
const StepUpSIPCalc = () => {
  const [monthlySIP, setMonthlySIP] = useState(5000);
  const [stepUp, setStepUp] = useState(10);
  const [years, setYears] = useState(15);
  const [rate, setRate] = useState(12);

  const result = useMemo(() => {
    const monthlyRate = rate / 12 / 100;
    let totalInvested = 0;
    let futureValue = 0;
    const yearlyData = [];

    for (let y = 1; y <= years; y++) {
      const currentSIP = monthlySIP * Math.pow(1 + stepUp / 100, y - 1);
      for (let m = 0; m < 12; m++) {
        totalInvested += currentSIP;
        futureValue = (futureValue + currentSIP) * (1 + monthlyRate);
      }
      yearlyData.push({ year: `${y}Y`, invested: Math.round(totalInvested), value: Math.round(futureValue), sip: Math.round(currentSIP) });
    }

    return { totalInvested: Math.round(totalInvested), futureValue: Math.round(futureValue), wealthGained: Math.round(futureValue - totalInvested), yearlyData };
  }, [monthlySIP, stepUp, years, rate]);

  const pieData = [
    { name: "Invested", value: result.totalInvested },
    { name: "Returns", value: result.wealthGained },
  ];

  return (
    <div className="space-y-8">
      <div className="space-y-6">
        {[
          { label: "Starting Monthly SIP", value: fmt(monthlySIP), state: monthlySIP, set: setMonthlySIP, min: 500, max: 100000, step: 500 },
          { label: "Annual Step-Up (%)", value: `${stepUp}%`, state: stepUp, set: setStepUp, min: 0, max: 50, step: 1 },
          { label: "Investment Period", value: `${years} Years`, state: years, set: setYears, min: 1, max: 30, step: 1 },
          { label: "Expected Return (p.a.)", value: `${rate}%`, state: rate, set: setRate, min: 1, max: 30, step: 0.5 },
        ].map((s) => (
          <div key={s.label}>
            <div className="flex justify-between mb-2">
              <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>{s.label}</label>
              <span className="text-sm font-bold text-primary">{s.value}</span>
            </div>
            <Slider value={[s.state]} onValueChange={([v]) => s.set(v)} min={s.min} max={s.max} step={s.step} />
          </div>
        ))}
      </div>

      <div className="bg-muted/50 rounded-xl p-4 text-center">
        <p className="text-xs text-muted-foreground">Your SIP grows from <strong>{fmt(monthlySIP)}</strong>/month to <strong>{fmt(monthlySIP * Math.pow(1 + stepUp / 100, years - 1))}</strong>/month by year {years}</p>
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
            <p className="text-sm font-bold text-foreground">{fmt(item.value)}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" stroke="none">
              <Cell fill={COLORS[0]} />
              <Cell fill={COLORS[1]} />
            </Pie>
            <Tooltip formatter={(v: number) => fmt(v)} />
          </PieChart>
        </ResponsiveContainer>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={result.yearlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 13%, 88%)" />
            <XAxis dataKey="year" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={fmt} tick={{ fontSize: 10 }} width={70} />
            <Tooltip formatter={(v: number) => fmt(v)} />
            <Area type="monotone" dataKey="invested" stroke={COLORS[0]} fill={COLORS[0]} fillOpacity={0.3} name="Invested" />
            <Area type="monotone" dataKey="value" stroke={COLORS[1]} fill={COLORS[1]} fillOpacity={0.3} name="Total Value" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// SWP Calculator
const SWPCalc = () => {
  const [corpus, setCorpus] = useState(5000000);
  const [withdrawal, setWithdrawal] = useState(25000);
  const [years, setYears] = useState(20);
  const [rate, setRate] = useState(8);

  const result = useMemo(() => {
    const monthlyRate = rate / 12 / 100;
    let balance = corpus;
    let totalWithdrawn = 0;
    const yearlyData = [];

    for (let y = 1; y <= years; y++) {
      for (let m = 0; m < 12; m++) {
        balance = balance * (1 + monthlyRate) - withdrawal;
        totalWithdrawn += withdrawal;
        if (balance < 0) { balance = 0; break; }
      }
      yearlyData.push({ year: `${y}Y`, balance: Math.round(Math.max(balance, 0)), withdrawn: Math.round(totalWithdrawn) });
      if (balance <= 0) break;
    }

    const lastYear = balance > 0 ? years : yearlyData.length;
    return { totalWithdrawn: Math.round(totalWithdrawn), remainingBalance: Math.round(Math.max(balance, 0)), lastsYears: lastYear, yearlyData };
  }, [corpus, withdrawal, years, rate]);

  const pieData = [
    { name: "Withdrawn", value: result.totalWithdrawn },
    { name: "Remaining", value: result.remainingBalance },
  ];

  return (
    <div className="space-y-8">
      <div className="space-y-6">
        {[
          { label: "Initial Corpus", value: fmt(corpus), state: corpus, set: setCorpus, min: 100000, max: 100000000, step: 100000 },
          { label: "Monthly Withdrawal", value: fmt(withdrawal), state: withdrawal, set: setWithdrawal, min: 1000, max: 500000, step: 1000 },
          { label: "Period", value: `${years} Years`, state: years, set: setYears, min: 1, max: 40, step: 1 },
          { label: "Expected Return (p.a.)", value: `${rate}%`, state: rate, set: setRate, min: 1, max: 20, step: 0.5 },
        ].map((s) => (
          <div key={s.label}>
            <div className="flex justify-between mb-2">
              <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>{s.label}</label>
              <span className="text-sm font-bold text-primary">{s.value}</span>
            </div>
            <Slider value={[s.state]} onValueChange={([v]) => s.set(v)} min={s.min} max={s.max} step={s.step} />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Withdrawn", value: result.totalWithdrawn, icon: ArrowDownRight },
          { label: "Remaining Balance", value: result.remainingBalance, icon: IndianRupee },
          { label: "Lasts For", value: null, display: `${result.lastsYears} Years`, icon: Target },
        ].map((item) => (
          <div key={item.label} className="bg-muted/50 rounded-xl p-4 text-center">
            <item.icon className="w-5 h-5 text-primary mx-auto mb-1" />
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="text-sm font-bold text-foreground">{item.display || fmt(item.value!)}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" stroke="none">
              <Cell fill={COLORS[2]} />
              <Cell fill={COLORS[1]} />
            </Pie>
            <Tooltip formatter={(v: number) => fmt(v)} />
          </PieChart>
        </ResponsiveContainer>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={result.yearlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 13%, 88%)" />
            <XAxis dataKey="year" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={fmt} tick={{ fontSize: 10 }} width={70} />
            <Tooltip formatter={(v: number) => fmt(v)} />
            <Area type="monotone" dataKey="balance" stroke={COLORS[1]} fill={COLORS[1]} fillOpacity={0.3} name="Balance" />
            <Area type="monotone" dataKey="withdrawn" stroke={COLORS[2]} fill={COLORS[2]} fillOpacity={0.3} name="Withdrawn" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Goal Planner
const GoalPlanner = () => {
  const [goalAmount, setGoalAmount] = useState(5000000);
  const [years, setYears] = useState(10);
  const [rate, setRate] = useState(12);
  const [stepUp, setStepUp] = useState(10);

  const result = useMemo(() => {
    // Calculate required monthly SIP (with step-up) to reach goal
    const monthlyRate = rate / 12 / 100;

    // Binary search for starting SIP
    let lo = 100, hi = 10000000, sip = 0;
    for (let i = 0; i < 100; i++) {
      const mid = (lo + hi) / 2;
      let fv = 0;
      for (let y = 0; y < years; y++) {
        const currentSIP = mid * Math.pow(1 + stepUp / 100, y);
        for (let m = 0; m < 12; m++) {
          fv = (fv + currentSIP) * (1 + monthlyRate);
        }
      }
      if (fv < goalAmount) lo = mid; else hi = mid;
      sip = mid;
    }

    const startingSIP = Math.ceil(hi);
    let totalInvested = 0;
    const yearlyData = [];
    let fv = 0;
    for (let y = 1; y <= years; y++) {
      const currentSIP = startingSIP * Math.pow(1 + stepUp / 100, y - 1);
      for (let m = 0; m < 12; m++) {
        totalInvested += currentSIP;
        fv = (fv + currentSIP) * (1 + monthlyRate);
      }
      yearlyData.push({ year: `${y}Y`, invested: Math.round(totalInvested), value: Math.round(fv), goal: goalAmount });
    }

    return { startingSIP, totalInvested: Math.round(totalInvested), yearlyData };
  }, [goalAmount, years, rate, stepUp]);

  return (
    <div className="space-y-8">
      <div className="space-y-6">
        {[
          { label: "Goal Amount", value: fmt(goalAmount), state: goalAmount, set: setGoalAmount, min: 100000, max: 100000000, step: 100000 },
          { label: "Time to Goal", value: `${years} Years`, state: years, set: setYears, min: 1, max: 30, step: 1 },
          { label: "Expected Return (p.a.)", value: `${rate}%`, state: rate, set: setRate, min: 1, max: 30, step: 0.5 },
          { label: "Annual Step-Up (%)", value: `${stepUp}%`, state: stepUp, set: setStepUp, min: 0, max: 50, step: 1 },
        ].map((s) => (
          <div key={s.label}>
            <div className="flex justify-between mb-2">
              <label className="text-sm font-medium text-foreground" style={{ fontFamily: "DM Sans" }}>{s.label}</label>
              <span className="text-sm font-bold text-primary">{s.value}</span>
            </div>
            <Slider value={[s.state]} onValueChange={([v]) => s.set(v)} min={s.min} max={s.max} step={s.step} />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-primary/10 rounded-xl p-4 text-center border border-primary/20">
          <ArrowUpRight className="w-5 h-5 text-primary mx-auto mb-1" />
          <p className="text-xs text-muted-foreground">Start SIP at</p>
          <p className="text-lg font-bold text-primary">{fmt(result.startingSIP)}/mo</p>
        </div>
        <div className="bg-muted/50 rounded-xl p-4 text-center">
          <IndianRupee className="w-5 h-5 text-primary mx-auto mb-1" />
          <p className="text-xs text-muted-foreground">Total Investment</p>
          <p className="text-sm font-bold text-foreground">{fmt(result.totalInvested)}</p>
        </div>
        <div className="bg-muted/50 rounded-xl p-4 text-center">
          <Target className="w-5 h-5 text-primary mx-auto mb-1" />
          <p className="text-xs text-muted-foreground">Goal Amount</p>
          <p className="text-sm font-bold text-foreground">{fmt(goalAmount)}</p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={result.yearlyData}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 13%, 88%)" />
          <XAxis dataKey="year" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={fmt} tick={{ fontSize: 10 }} width={70} />
          <Tooltip formatter={(v: number) => fmt(v)} />
          <Area type="monotone" dataKey="invested" stroke={COLORS[0]} fill={COLORS[0]} fillOpacity={0.2} name="Invested" />
          <Area type="monotone" dataKey="value" stroke={COLORS[1]} fill={COLORS[1]} fillOpacity={0.3} name="Portfolio Value" />
          <Area type="step" dataKey="goal" stroke={COLORS[2]} fill="none" strokeDasharray="5 5" name="Goal" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

const GoalCalculatorPage = () => {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="absolute top-20 right-0 w-[300px] h-[300px] bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-20 left-0 w-[250px] h-[250px] bg-secondary/5 rounded-full blur-3xl" />
      <Navbar />
      <main className="pt-24 pb-16">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-12 animate-fade-up">
            <div className="inline-flex items-center gap-2 gradient-primary text-white px-4 py-2 rounded-full text-sm font-medium mb-4 shadow-lg">
              <Target className="w-4 h-4" /> Goal Planning
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-foreground mb-4">
              Advanced <span className="gradient-text">Calculators</span>
            </h1>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Plan with Step-Up SIP, SWP withdrawals, or reverse-engineer your SIP from a financial goal.
            </p>
          </div>

          <Card className="max-w-4xl mx-auto border-border/50 shadow-2xl animate-fade-up" style={{ animationDelay: '0.1s' }}>
            <CardHeader>
              <Tabs defaultValue="stepup" className="w-full">
                <TabsList className="grid w-full grid-cols-3 mb-6">
                  <TabsTrigger value="stepup" className="text-xs sm:text-sm font-semibold gap-1">
                    <ArrowUpRight className="w-4 h-4" /> Step-Up SIP
                  </TabsTrigger>
                  <TabsTrigger value="swp" className="text-xs sm:text-sm font-semibold gap-1">
                    <ArrowDownRight className="w-4 h-4" /> SWP
                  </TabsTrigger>
                  <TabsTrigger value="goal" className="text-xs sm:text-sm font-semibold gap-1">
                    <Target className="w-4 h-4" /> Goal Planner
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="stepup"><StepUpSIPCalc /></TabsContent>
                <TabsContent value="swp"><SWPCalc /></TabsContent>
                <TabsContent value="goal"><GoalPlanner /></TabsContent>
              </Tabs>
            </CardHeader>
          </Card>

          <div className="grid sm:grid-cols-3 gap-6 mt-16 max-w-4xl mx-auto">
            {[
              { title: "Step-Up SIP", desc: "Increase your SIP annually by a fixed percentage. Even a 10% annual step-up can double your corpus compared to a flat SIP." },
              { title: "SWP Strategy", desc: "Systematic Withdrawal Plan lets you withdraw a fixed amount monthly from your corpus while the rest continues to grow." },
              { title: "Goal Planning", desc: "Define your target amount and timeline. We'll calculate the exact starting SIP you need, with step-up, to reach your goal." },
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

export default GoalCalculatorPage;
