import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";

export default function ChangePassword() {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      toast({
        title: "Error",
        description: "Passwords do not match.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const csrftoken = getCookie('csrftoken');
      const response = await fetch('/users/api/auth/change-password/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken || '',
        },
        body: JSON.stringify({ new_password: password }),
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        toast({
          title: "Password Changed",
          description: data.message,
        });

        // Re-check auth to get the correct dashboard URL based on user type
        const authResponse = await fetch('/users/api/auth/status/');
        const authData = await authResponse.json();

        if (authData.is_authenticated) {
            window.location.href = authData.redirect_url || '/dashboard/admin/';
        } else {
            navigate('/login');
        }

      } else {
        throw new Error(data.message || 'Failed to change password');
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
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden bg-background">
      <div className="w-full max-w-md relative animate-fade-up">
        <Card className="border-border/50 shadow-2xl backdrop-blur-sm bg-card/90">
          <CardHeader className="text-center space-y-4">
            <div>
              <CardTitle className="text-2xl">Change Password Required</CardTitle>
              <CardDescription className="text-muted-foreground mt-2">
                For security reasons, please change your password before continuing.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2 relative">
                  <Label htmlFor="password">New Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter new password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="h-12 bg-background/50 focus:bg-background transition-colors"
                  />
                  <p className="text-xs text-muted-foreground">
                    Must be at least 8 characters, include 1 uppercase, 1 lowercase, and 1 special character.
                  </p>
                </div>

                <div className="space-y-2 relative">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="Confirm new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    className="h-12 bg-background/50 focus:bg-background transition-colors"
                  />
                </div>
              </div>

              <Button type="submit" className="w-full h-12 text-base font-semibold transition-all hover:scale-[1.02]" disabled={loading}>
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Change Password"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
