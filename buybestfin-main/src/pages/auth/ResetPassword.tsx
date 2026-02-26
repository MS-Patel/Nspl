import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import logo from "@/assets/logo.png";

const ResetPassword = () => {
  const { uid, token } = useParams();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
        toast({ title: "Error", description: "Passwords do not match.", variant: "destructive" });
        return;
    }
    setLoading(true);

    try {
      const response: any = await api.post('/api/auth/password-reset/confirm/', {
          uid,
          token,
          password
      });
      if (response.status === 'success') {
          toast({
              title: "Success",
              description: "Password reset successfully. Please login.",
          });
          navigate('/login');
      } else {
          throw new Error(response.error || "Failed to reset password.");
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.error || error.message || "Invalid or expired link.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-secondary/10" />
        <Card className="w-full max-w-md relative border-border/50 shadow-2xl backdrop-blur-sm bg-card/90">
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto">
              <img src={logo} alt="BuyBestFin" className="w-16 h-16 rounded-2xl mx-auto shadow-lg" />
            </div>
            <CardTitle className="text-2xl">Set New Password</CardTitle>
            <CardDescription>Enter your new password below.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password">New Password</Label>
                <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                    id="confirmPassword"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={8}
                />
              </div>
              <Button className="w-full gradient-primary border-0 text-white hover:opacity-90" size="lg" disabled={loading}>
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                Reset Password
              </Button>
            </form>
          </CardContent>
        </Card>
    </div>
  );
};

export default ResetPassword;
