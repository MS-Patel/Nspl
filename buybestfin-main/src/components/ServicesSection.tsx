import { TrendingUp, BarChart3, Shield, Landmark, PieChart, Layers } from "lucide-react";

const services = [
  {
    icon: PieChart,
    title: "Mutual Funds",
    description: "Invest in top-performing mutual funds via SIP or Lumpsum. Access 5000+ schemes across equity, debt, and hybrid categories from all major AMCs.",
    features: ["SIP Starting ₹500", "All AMC Schemes", "Goal-Based Planning"],
    gradient: "from-primary/5 to-accent/5",
  },
  {
    icon: TrendingUp,
    title: "Unlisted Equities",
    description: "Get early access to high-growth companies before they go public. Pre-IPO shares of top Indian startups and enterprises.",
    features: ["Pre-IPO Shares", "High Growth Potential", "Expert Curation"],
    gradient: "from-secondary/5 to-primary/5",
  },
  {
    icon: BarChart3,
    title: "Listed Equities",
    description: "Build a strong equity portfolio with direct stock investments. Research-backed recommendations for long-term wealth creation.",
    features: ["Research Backed", "Portfolio Advisory", "Long Term Growth"],
    gradient: "from-accent/5 to-secondary/5",
  },
  {
    icon: Landmark,
    title: "Bonds",
    description: "Invest in government and corporate bonds for stable, predictable returns. Ideal for conservative investors seeking regular income.",
    features: ["Govt & Corporate", "Regular Income", "Capital Safety"],
    gradient: "from-primary/5 to-secondary/5",
  },
  {
    icon: Shield,
    title: "Corporate FDs",
    description: "Earn higher interest rates compared to bank FDs with AAA-rated corporate fixed deposits. Safe and secure investment option.",
    features: ["Higher Returns", "AAA Rated", "Flexible Tenure"],
    gradient: "from-secondary/5 to-accent/5",
  },
  {
    icon: Layers,
    title: "Portfolio Management",
    description: "Comprehensive portfolio review and rebalancing services. We help optimize your asset allocation for maximum risk-adjusted returns.",
    features: ["Asset Allocation", "Regular Rebalancing", "Risk Management"],
    gradient: "from-accent/5 to-primary/5",
  },
];

const ServicesSection = () => {
  return (
    <section id="services" className="py-24 bg-background relative overflow-hidden">
      {/* Decorative background */}
      <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-[250px] h-[250px] bg-secondary/5 rounded-full blur-3xl" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div className="text-center mb-16">
          <p className="text-sm font-semibold text-secondary uppercase tracking-wider mb-2">Our Services</p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Complete <span className="gradient-text">Investment Solutions</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            From mutual funds to unlisted equities, we offer a comprehensive range of investment 
            products tailored to your financial goals.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((service, i) => (
            <div
              key={i}
              className={`group bg-gradient-to-br ${service.gradient} border border-border/50 rounded-2xl p-8 hover:shadow-xl hover:-translate-y-1 transition-all duration-500`}
            >
              <div className="w-14 h-14 rounded-2xl gradient-primary flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform duration-300">
                <service.icon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-3" style={{ fontFamily: 'DM Sans' }}>{service.title}</h3>
              <p className="text-muted-foreground text-sm mb-5 leading-relaxed">{service.description}</p>
              <div className="flex flex-wrap gap-2">
                {service.features.map((feature, j) => (
                  <span
                    key={j}
                    className="text-xs font-medium bg-card text-muted-foreground px-3 py-1 rounded-full border border-border/50"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default ServicesSection;
