import { CheckCircle2, Sparkles } from "lucide-react";

const AboutSection = () => {
  return (
    <section id="about" className="py-24 relative overflow-hidden">
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/3 via-background to-secondary/3" />
      <div className="absolute top-20 left-0 w-[200px] h-[200px] bg-accent/8 rounded-full blur-3xl" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <p className="text-sm font-semibold text-secondary uppercase tracking-wider mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4" /> About Us
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-6">
              Your Trusted <span className="gradient-text">Financial Partner</span> Since Day One
            </h2>
            <p className="text-muted-foreground mb-8 leading-relaxed">
              BuyBestFin is an AMFI Registered Mutual Fund Distributor (ARN: 147231). 
              We are committed to helping individuals and businesses achieve their financial 
              goals through expert guidance and a wide range of investment products.
            </p>

            <div className="space-y-4">
              {[
                "AMFI Registered MFD (ARN: 147231)",
                "Comprehensive range of investment products",
                "Personalized financial planning & advisory",
                "Transparent and client-first approach",
                "Technology-driven investment platform",
                "Dedicated support for customers & partners",
              ].map((item, i) => (
                <div key={i} className="flex items-start gap-3 group">
                  <CheckCircle2 className="w-5 h-5 text-secondary mt-0.5 shrink-0 group-hover:scale-110 transition-transform" />
                  <span className="text-foreground text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gradient-to-br from-card to-primary/5 border border-border/50 rounded-3xl p-10 space-y-8 shadow-xl">
            <div className="text-center">
              <h3 className="text-2xl font-bold text-foreground mb-2" style={{ fontFamily: 'DM Sans' }}>Why Choose Us?</h3>
              <p className="text-muted-foreground text-sm">We go beyond just selling products</p>
            </div>

            <div className="grid grid-cols-2 gap-6">
              {[
                { value: "147231", label: "ARN Number", color: "from-primary/10 to-accent/10" },
                { value: "500+", label: "Clients Served", color: "from-secondary/10 to-primary/10" },
                { value: "5000+", label: "MF Schemes", color: "from-accent/10 to-secondary/10" },
                { value: "24/7", label: "Online Access", color: "from-primary/10 to-secondary/10" },
              ].map((stat, i) => (
                <div key={i} className={`text-center p-4 rounded-2xl bg-gradient-to-br ${stat.color} hover:scale-105 transition-transform duration-300`}>
                  <p className="text-2xl font-bold gradient-text">{stat.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
                </div>
              ))}
            </div>

            <div className="gradient-primary rounded-2xl p-6 text-center">
              <p className="text-sm text-white font-medium">
                "Mutual Fund investments are subject to market risks. Please read all scheme related documents carefully before investing."
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default AboutSection;
