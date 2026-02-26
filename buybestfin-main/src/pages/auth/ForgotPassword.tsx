import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import logo from "@/assets/logo.png";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response: any = await api.post('/api/auth/password-reset/request/', { email });
      if (response.status === 'success') {
          setSuccess(true);
          toast({
              title: "Reset Link Sent",
              description: response.message,
          });
      } else {
          throw new Error(response.error || "Failed to send reset link.");
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.error || error.message || "An error occurred.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-secondary/10" />
      <div className="w-full max-w-md relative animate-fade-up">
        <Link to="/login" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Login
        </Link>

        <Card className="border-border/50 shadow-2xl backdrop-blur-sm bg-card/90">
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto">
              <img src={logo} alt="BuyBestFin" className="w-16 h-16 rounded-2xl mx-auto shadow-lg" />
            </div>
            <CardTitle className="text-2xl">Reset Password</CardTitle>
            <CardDescription>
                Enter your email address and we'll send you a link to reset your password.
            </CardDescription>
          </CardHeader>
          <CardContent>
             {success ? (
                 <div className="text-center space-y-4">
                     <p className="text-sm text-green-600 font-medium">Check your email for the reset link.</p>
                     <Link to="/login">
                        <Button variant="outline" className="w-full">Return to Login</Button>
                     </Link>
                 </div>
             ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="name@example.com"
                        required
                    />
                </div>
                <Button className="w-full gradient-primary border-0 text-white hover:opacity-90" size="lg" disabled={loading}>
                    {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                    Send Reset Link
                </Button>
                </form>
             )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ForgotPassword;
