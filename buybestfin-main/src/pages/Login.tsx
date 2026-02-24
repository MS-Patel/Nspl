import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import logo from "@/assets/logo.png";

const Login = () => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isRegister) {
        toast({
          title: "Registration not available",
          description: "Please contact support to create an account.",
          variant: "destructive",
        });
      } else {
        // CSRF Token
        const getCookie = (name: string) => {
          let cookieValue = null;
          if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
              const cookie = cookies[i].trim();
              if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
              }
            }
          }
          return cookieValue;
        }
        const csrftoken = getCookie('csrftoken');

        const response = await fetch('/users/api/auth/login/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken || '',
          },
          body: JSON.stringify({ username: email, password: password }),
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
          toast({
            title: "Login successful!",
            description: "Redirecting...",
          });
          window.location.href = data.redirect_url || '/dashboard/admin/';
        } else {
          throw new Error(data.message || 'Login failed');
        }
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-secondary/10" />
      <div className="absolute top-20 right-20 w-[300px] h-[300px] bg-primary/8 rounded-full blur-3xl animate-float" />
      <div className="absolute bottom-20 left-20 w-[250px] h-[250px] bg-secondary/8 rounded-full blur-3xl animate-float" style={{ animationDelay: '1.5s' }} />

      <div className="w-full max-w-md relative animate-fade-up">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>

        <Card className="border-border/50 shadow-2xl backdrop-blur-sm bg-card/90">
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto">
              <img src={logo} alt="BuyBestFin" className="w-16 h-16 rounded-2xl mx-auto shadow-lg" />
            </div>
            <div>
              <CardTitle className="text-2xl">
                {isRegister ? "Create Account" : "Welcome Back"}
              </CardTitle>
              <CardDescription className="mt-1">
                {isRegister
                  ? "Sign up to start your investment journey"
                  : "Sign in to access your portal"}
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {isRegister && (
                <div className="space-y-2">
                  <Label htmlFor="fullName">Full Name</Label>
                  <Input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Your full name" required />
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Username / Email</Label>
                <Input id="email" type="text" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Username or Email" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required minLength={6} />
              </div>
              <Button className="w-full gradient-primary border-0 text-white hover:opacity-90" size="lg" disabled={loading}>
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {isRegister ? "Create Account" : "Sign In"}
              </Button>
            </form>

            <p className="text-center text-sm text-muted-foreground mt-4">
              {isRegister ? "Already have an account?" : "Don't have an account?"}{" "}
              <button onClick={() => setIsRegister(!isRegister)} className="text-primary font-medium hover:underline">
                {isRegister ? "Sign In" : "Register here"}
              </button>
            </p>

            <p className="text-xs text-muted-foreground text-center mt-6">
              BuyBestFin | ARN: 147231
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Login;
