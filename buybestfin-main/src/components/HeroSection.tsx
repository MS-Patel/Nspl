import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowRight, Shield, TrendingUp, IndianRupee, BarChart3 } from "lucide-react";

const HeroSection = () => {
  return (
    <section className="relative min-h-screen flex items-center pt-16 overflow-hidden">
      {/* Background decorations */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-secondary/5" />
      <div className="absolute top-20 right-0 w-[500px] h-[500px] bg-primary/8 rounded-full blur-3xl animate-pulse-glow" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-secondary/10 rounded-full blur-3xl" />
      <div className="absolute top-40 left-1/4 w-[200px] h-[200px] bg-accent/8 rounded-full blur-2xl animate-float" />
      
      {/* Floating decorative elements */}
      <div className="absolute top-32 right-20 w-16 h-16 rounded-2xl gradient-primary opacity-10 animate-float" style={{ animationDelay: '1s' }} />
      <div className="absolute bottom-40 left-20 w-12 h-12 rounded-full bg-secondary/20 animate-float" style={{ animationDelay: '2s' }} />
      <div className="absolute top-60 right-1/3 w-8 h-8 rounded-lg bg-accent/15 animate-float" style={{ animationDelay: '0.5s' }} />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium animate-fade-up">
              <Shield className="w-4 h-4" />
              AMFI Registered Mutual Fund Distributor
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground leading-tight animate-fade-up" style={{ animationDelay: '0.1s' }}>
              Grow Your Wealth with{" "}
              <span className="gradient-text">Smart Investments</span>
            </h1>

            <p className="text-lg text-muted-foreground max-w-lg animate-fade-up" style={{ animationDelay: '0.2s' }}>
              Your trusted partner for Mutual Funds, Equities, Bonds & Corporate FDs.
              We help you build a diversified portfolio for long-term wealth creation.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 animate-fade-up" style={{ animationDelay: '0.3s' }}>
              <Link to="/login">
                <Button size="lg" className="gap-2 text-base px-8 gradient-primary border-0 text-white hover:opacity-90 transition-opacity shadow-lg">
                  Start Investing <ArrowRight className="w-5 h-5" />
                </Button>
              </Link>
              <a href="#services">
                <Button size="lg" variant="outline" className="gap-2 text-base px-8 border-primary/30 hover:border-primary hover:bg-primary/5 transition-all">
                  Explore Services
                </Button>
              </a>
            </div>

            <div className="flex items-center gap-8 pt-4 animate-fade-up" style={{ animationDelay: '0.4s' }}>
              {[
                { value: "500+", label: "Happy Clients" },
                { value: "₹50Cr+", label: "AUM Managed" },
                { value: "10+", label: "Years Experience" },
              ].map((stat, i) => (
                <div key={stat.label} className="flex items-center gap-4">
                  {i > 0 && <div className="w-px h-10 bg-border" />}
                  <div>
                    <p className="text-2xl font-bold gradient-text">{stat.value}</p>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="hidden lg:grid grid-cols-2 gap-4">
            {[
              { icon: TrendingUp, title: "Mutual Funds", desc: "SIP & Lumpsum across top AMCs", gradient: "from-primary/10 to-accent/10", iconColor: "text-primary" },
              { icon: IndianRupee, title: "Listed Equities", desc: "Direct equity investments", gradient: "from-secondary/10 to-accent/10", iconColor: "text-secondary" },
              { icon: Shield, title: "Bonds", desc: "Government & Corporate bonds", gradient: "from-accent/10 to-primary/10", iconColor: "text-accent" },
              { icon: BarChart3, title: "Corporate FDs", desc: "High-yield fixed deposits", gradient: "from-primary/10 to-secondary/10", iconColor: "text-primary" },
            ].map((item, i) => (
              <div
                key={i}
                className={`bg-gradient-to-br ${item.gradient} border border-border/50 rounded-2xl p-6 hover:shadow-xl hover:-translate-y-2 transition-all duration-500 animate-scale-in backdrop-blur-sm`}
                style={{ animationDelay: `${0.2 + i * 0.15}s` }}
              >
                <div className={`w-12 h-12 rounded-xl bg-card/80 flex items-center justify-center mb-4 shadow-sm`}>
                  <item.icon className={`w-6 h-6 ${item.iconColor}`} />
                </div>
                <h3 className="font-semibold text-foreground mb-1" style={{ fontFamily: 'DM Sans' }}>{item.title}</h3>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
