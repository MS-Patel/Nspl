import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, LogOut, User, PieChart, BarChart3, Shield, Landmark } from "lucide-react";

const Dashboard = () => {
  const [user, setUser] = useState<any | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [fullName, setFullName] = useState<string>("");
  const navigate = useNavigate();

  useEffect(() => {
    // Mock user for UI preview or redirect
    // In production, this route should be handled by Django
    setUser({ email: 'demo@example.com' });
    setFullName("Demo User");
  }, []);

  const handleLogout = async () => {
    window.location.href = "/users/logout/";
  };

  if (!user) return null;

  const roleLabel = "User";

  return (
    <div className="min-h-screen bg-background">
      {/* Top bar */}
      <header className="bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex justify-between items-center h-16">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-foreground" style={{ fontFamily: 'DM Sans' }}>BuyBestFin</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-foreground">{fullName || user.email}</p>
              <p className="text-xs text-muted-foreground">{roleLabel}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <h1 className="text-3xl font-bold text-foreground mb-2">Welcome, {fullName || "User"}!</h1>
        <p className="text-muted-foreground mb-8">
          You are logged in as <span className="font-semibold text-primary">{roleLabel}</span>.
        </p>
         <p className="mb-4">
            <a href="/dashboard/admin/" className="text-primary hover:underline">Go to Admin Dashboard</a>
         </p>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          {[
            { icon: PieChart, title: "Mutual Funds", value: "View Portfolio", color: "text-primary" },
            { icon: BarChart3, title: "Equities", value: "Track Holdings", color: "text-accent" },
            { icon: Shield, title: "Bonds", value: "View Bonds", color: "text-primary" },
            { icon: Landmark, title: "Corporate FDs", value: "View FDs", color: "text-accent" },
          ].map((item, i) => (
            <Card key={i} className="hover:shadow-md transition-shadow cursor-pointer">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground" style={{ fontFamily: 'DM Sans' }}>
                  {item.title}
                </CardTitle>
                <item.icon className={`w-5 h-5 ${item.color}`} />
              </CardHeader>
              <CardContent>
                <p className="text-lg font-bold text-foreground">{item.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
