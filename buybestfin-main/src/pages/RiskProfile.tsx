import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { toast } from "@/hooks/use-toast";
import { ShieldCheck, ArrowRight, ArrowLeft, RotateCcw, Target, TrendingUp, Scale } from "lucide-react";

const QUESTIONS = [
  {
    id: "age",
    question: "What is your age group?",
    options: [
      { label: "18–25 years", value: "18-25", score: 10 },
      { label: "26–35 years", value: "26-35", score: 8 },
      { label: "36–50 years", value: "36-50", score: 5 },
      { label: "Above 50 years", value: "50+", score: 2 },
    ],
  },
  {
    id: "income",
    question: "What is your annual income?",
    options: [
      { label: "Below ₹5 Lakh", value: "<5L", score: 3 },
      { label: "₹5–15 Lakh", value: "5-15L", score: 5 },
      { label: "₹15–30 Lakh", value: "15-30L", score: 8 },
      { label: "Above ₹30 Lakh", value: ">30L", score: 10 },
    ],
  },
  {
    id: "investment_horizon",
    question: "What is your investment horizon?",
    options: [
      { label: "Less than 1 year", value: "<1Y", score: 2 },
      { label: "1–3 years", value: "1-3Y", score: 4 },
      { label: "3–7 years", value: "3-7Y", score: 7 },
      { label: "More than 7 years", value: ">7Y", score: 10 },
    ],
  },
  {
    id: "loss_reaction",
    question: "If your investment drops by 20%, what would you do?",
    options: [
      { label: "Sell everything immediately", value: "sell_all", score: 1 },
      { label: "Sell some and wait", value: "sell_some", score: 4 },
      { label: "Hold and wait for recovery", value: "hold", score: 7 },
      { label: "Buy more at lower prices", value: "buy_more", score: 10 },
    ],
  },
  {
    id: "investment_goal",
    question: "What is your primary investment goal?",
    options: [
      { label: "Preserve capital at all costs", value: "preserve", score: 2 },
      { label: "Regular income with low risk", value: "income", score: 4 },
      { label: "Balanced growth and income", value: "balanced", score: 7 },
      { label: "Maximum wealth creation", value: "growth", score: 10 },
    ],
  },
  {
    id: "experience",
    question: "How would you describe your investing experience?",
    options: [
      { label: "No experience (first-time investor)", value: "none", score: 2 },
      { label: "Some experience (FD, RD, savings)", value: "basic", score: 4 },
      { label: "Moderate (mutual funds, stocks)", value: "moderate", score: 7 },
      { label: "Advanced (derivatives, commodities)", value: "advanced", score: 10 },
    ],
  },
  {
    id: "dependents",
    question: "How many financial dependents do you have?",
    options: [
      { label: "None", value: "0", score: 10 },
      { label: "1–2 dependents", value: "1-2", score: 7 },
      { label: "3–4 dependents", value: "3-4", score: 4 },
      { label: "5 or more", value: "5+", score: 2 },
    ],
  },
  {
    id: "emergency_fund",
    question: "Do you have an emergency fund (3–6 months expenses)?",
    options: [
      { label: "No emergency fund", value: "none", score: 2 },
      { label: "Less than 3 months", value: "<3m", score: 4 },
      { label: "3–6 months covered", value: "3-6m", score: 7 },
      { label: "More than 6 months covered", value: ">6m", score: 10 },
    ],
  },
];

const getRiskCategory = (score: number) => {
  if (score <= 30) return { category: "Conservative", color: "gradient-primary", desc: "You prefer safety and capital preservation. Ideal funds: Debt funds, Liquid funds, Short Duration funds.", icon: ShieldCheck };
  if (score <= 50) return { category: "Moderately Conservative", color: "bg-accent", desc: "You lean towards safety but are open to some growth. Ideal funds: Conservative Hybrid, Dynamic Bond funds.", icon: Scale };
  if (score <= 70) return { category: "Moderate", color: "bg-secondary", desc: "You seek balanced risk-reward. Ideal funds: Balanced Advantage, Multi-asset, Flexi Cap funds.", icon: Target };
  if (score <= 85) return { category: "Moderately Aggressive", color: "bg-primary", desc: "You're comfortable with volatility for higher returns. Ideal funds: Large & Mid Cap, Flexi Cap, ELSS.", icon: TrendingUp };
  return { category: "Aggressive", color: "bg-destructive", desc: "You seek maximum growth and can handle high volatility. Ideal funds: Small Cap, Mid Cap, Sectoral/Thematic funds.", icon: TrendingUp };
};

const RiskProfile = () => {
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [showResult, setShowResult] = useState(false);
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const totalScore = Object.entries(answers).reduce((sum, [qId, val]) => {
    const q = QUESTIONS.find((q) => q.id === qId);
    const opt = q?.options.find((o) => o.value === val);
    return sum + (opt?.score || 0);
  }, 0);

  const maxScore = QUESTIONS.length * 10;
  const normalizedScore = Math.round((totalScore / maxScore) * 100);
  const riskInfo = getRiskCategory(normalizedScore);
  const progress = ((currentQ + 1) / QUESTIONS.length) * 100;

  const handleAnswer = (value: string) => {
    setAnswers((prev) => ({ ...prev, [QUESTIONS[currentQ].id]: value }));
  };

  const handleNext = () => {
    if (currentQ < QUESTIONS.length - 1) setCurrentQ((p) => p + 1);
    else setShowResult(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Mock save for now
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast({ title: "Risk profile saved locally (Demo Only)!" });
    } catch (err: any) {
      toast({ title: "Failed to save", description: err.message, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setCurrentQ(0);
    setAnswers({});
    setShowResult(false);
  };

  const currentQuestion = QUESTIONS[currentQ];
  const currentAnswer = answers[currentQuestion.id];

  if (showResult) {
    const RiskIcon = riskInfo.icon;
    return (
      <div className="min-h-screen bg-background relative overflow-hidden">
        <div className="absolute top-20 right-0 w-[300px] h-[300px] bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-20 left-0 w-[250px] h-[250px] bg-secondary/5 rounded-full blur-3xl" />
        <Navbar />
        <main className="pt-24 pb-16 max-w-2xl mx-auto px-4 relative animate-fade-up">
          <Card className="border-border/50 shadow-2xl">
            <CardHeader className="text-center">
              <div className={`w-16 h-16 rounded-full ${riskInfo.color} flex items-center justify-center mx-auto mb-4`}>
                <RiskIcon className="w-8 h-8 text-white" />
              </div>
              <CardTitle className="text-2xl">Your Risk Profile</CardTitle>
              <CardDescription>Based on your answers to {QUESTIONS.length} questions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center">
                <Badge className={`${riskInfo.color} text-white text-lg px-6 py-2`}>
                  {riskInfo.category}
                </Badge>
                <p className="text-4xl font-bold text-foreground mt-4 font-mono">{normalizedScore}/100</p>
                <Progress value={normalizedScore} className="mt-4 h-3" />
              </div>

              <div className="bg-muted/50 rounded-xl p-4">
                <p className="text-sm text-muted-foreground leading-relaxed">{riskInfo.desc}</p>
              </div>

              <div className="grid grid-cols-4 gap-1 text-center text-xs text-muted-foreground">
                {["Conservative", "Moderate", "Aggressive", "Very Aggressive"].map((l) => (
                  <div key={l} className="py-1">{l}</div>
                ))}
              </div>

              <div className="flex gap-3">
                <Button onClick={handleSave} disabled={saving} className="flex-1">
                  {saving ? "Saving..." : "Save Profile"}
                </Button>
                <Button variant="outline" onClick={handleReset} className="gap-2">
                  <RotateCcw className="w-4 h-4" /> Retake
                </Button>
              </div>

              <div className="pt-4 border-t border-border">
                <h4 className="font-semibold text-foreground mb-3" style={{ fontFamily: "DM Sans" }}>Recommended Fund Categories</h4>
                <div className="flex flex-wrap gap-2">
                  {normalizedScore <= 30 && ["Liquid Fund", "Ultra Short Duration", "Short Duration", "Corporate Bond"].map((f) => <Badge key={f} variant="secondary">{f}</Badge>)}
                  {normalizedScore > 30 && normalizedScore <= 50 && ["Conservative Hybrid", "Dynamic Bond", "Banking & PSU", "Equity Savings"].map((f) => <Badge key={f} variant="secondary">{f}</Badge>)}
                  {normalizedScore > 50 && normalizedScore <= 70 && ["Balanced Advantage", "Multi Asset", "Flexi Cap", "Large Cap"].map((f) => <Badge key={f} variant="secondary">{f}</Badge>)}
                  {normalizedScore > 70 && normalizedScore <= 85 && ["Large & Mid Cap", "Flexi Cap", "ELSS", "Value Fund"].map((f) => <Badge key={f} variant="secondary">{f}</Badge>)}
                  {normalizedScore > 85 && ["Small Cap", "Mid Cap", "Sectoral/Thematic", "International"].map((f) => <Badge key={f} variant="secondary">{f}</Badge>)}
                </div>
              </div>
            </CardContent>
          </Card>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="absolute top-20 right-0 w-[300px] h-[300px] bg-secondary/5 rounded-full blur-3xl animate-float" />
      <div className="absolute bottom-40 left-0 w-[200px] h-[200px] bg-primary/5 rounded-full blur-3xl" />
      <Navbar />
      <main className="pt-24 pb-16 max-w-2xl mx-auto px-4 relative">
        <div className="text-center mb-8 animate-fade-up">
          <div className="inline-flex items-center gap-2 gradient-primary text-white px-4 py-2 rounded-full text-sm font-medium mb-4 shadow-lg">
            <ShieldCheck className="w-4 h-4" /> Risk Analyzer
          </div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Know Your <span className="gradient-text">Risk Profile</span></h1>
          <p className="text-muted-foreground">Answer {QUESTIONS.length} simple questions to discover your investor personality.</p>
        </div>

        <Card className="border-border/50 shadow-2xl animate-fade-up" style={{ animationDelay: '0.1s' }}>
          <CardHeader>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted-foreground font-medium">Question {currentQ + 1} of {QUESTIONS.length}</span>
              <span className="text-xs text-muted-foreground font-mono">{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
            <CardTitle className="text-lg mt-4" style={{ fontFamily: "DM Sans" }}>{currentQuestion.question}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <RadioGroup value={currentAnswer || ""} onValueChange={handleAnswer}>
              {currentQuestion.options.map((opt) => (
                <div
                  key={opt.value}
                  className={`flex items-center gap-3 p-4 rounded-xl border transition-all cursor-pointer ${
                    currentAnswer === opt.value ? "border-primary bg-primary/5" : "border-border hover:border-primary/30"
                  }`}
                  onClick={() => handleAnswer(opt.value)}
                >
                  <RadioGroupItem value={opt.value} id={opt.value} />
                  <Label htmlFor={opt.value} className="cursor-pointer flex-1 text-sm font-medium">
                    {opt.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>

            <div className="flex justify-between pt-4">
              <Button variant="outline" onClick={() => setCurrentQ((p) => p - 1)} disabled={currentQ === 0} className="gap-2">
                <ArrowLeft className="w-4 h-4" /> Previous
              </Button>
              <Button onClick={handleNext} disabled={!currentAnswer} className="gap-2">
                {currentQ === QUESTIONS.length - 1 ? "See Result" : "Next"} <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
      <Footer />
    </div>
  );
};

export default RiskProfile;
