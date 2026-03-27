import { useState, useEffect } from "react";
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
  const [isOTPLogin, setIsOTPLogin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [fullName, setFullName] = useState("");
  const [pan, setPan] = useState("");
  const [mobile, setMobile] = useState("");
  const [arnNumber, setArnNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/users/api/auth/status/');
        const data = await response.json();
        if (data.is_authenticated) {
          if (data.force_password_change) {
            window.location.href = '/dashboard/change-password';
          } else {
            window.location.href = data.redirect_url;
          }
        }
      } catch (error) {
        console.error("Auth check failed:", error);
      }
    };
    checkAuth();
  }, []);

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
  };

  const handleSendOTP = async () => {
    setLoading(true);
    try {
      const csrftoken = getCookie('csrftoken');
      const response = await fetch('/users/otp/send/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrftoken || '',
        },
        body: new URLSearchParams({ username: email }).toString(),
      });

      const data = await response.json();
      if (response.ok && data.status === 'success') {
        toast({
          title: "OTP Sent",
          description: data.message,
        });
        setOtpSent(true);
      } else {
        throw new Error(data.message || 'Failed to send OTP');
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

  const handleVerifyOTP = async () => {
    setLoading(true);
    try {
      const csrftoken = getCookie('csrftoken');
      const response = await fetch('/users/otp/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrftoken || '',
        },
        body: new URLSearchParams({ username: email, otp: otp }).toString(),
      });
      const data = await response.json();

      if (response.ok && data.status === 'success') {
        toast({
          title: "Login successful!",
          description: "Redirecting...",
        });
        if (data.force_password_change) {
          window.location.href = '/dashboard/change-password';
        } else {
          window.location.href = data.redirect_url || '/dashboard/admin/';
        }
      } else {
        throw new Error(data.message || 'Invalid OTP');
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isRegister) {
        const csrftoken = getCookie('csrftoken');
        const response = await fetch('/users/api/auth/register/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken || '',
          },
          body: JSON.stringify({
            name: fullName,
            email: email,
            password: password,
            pan: pan,
            mobile: mobile,
            arn_number: arnNumber,
          }),
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
          toast({
            title: "Registration successful!",
            description: "Your account has been created. You can now login.",
          });
          setIsRegister(false);
        } else {
          throw new Error(data.message || 'Registration failed');
        }
        setLoading(false);
      } else if (isOTPLogin) {
        if (!otpSent) {
          await handleSendOTP();
        } else {
          await handleVerifyOTP();
        }
      } else {
        // Password Login
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
          if (data.force_password_change) {
          window.location.href = '/dashboard/change-password';
        } else {
          window.location.href = data.redirect_url || '/dashboard/admin/';
        }
        } else {
          throw new Error(data.message || 'Login failed');
        }
        setLoading(false);
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsOTPLogin(!isOTPLogin);
    setOtpSent(false);
    setOtp("");
    setPassword("");
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
                {isRegister ? "Create Account" : (isOTPLogin ? "Login with OTP" : "Welcome Back")}
              </CardTitle>
              <CardDescription className="mt-1">
                {isRegister
                  ? "Sign up to start your investment journey"
                  : (isOTPLogin ? "Enter your username to receive an OTP" : "Sign in to access your portal")}
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
                <Label htmlFor="email">{isRegister ? "Email" : "Username / Email"}</Label>
                <Input
                  id="email"
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Username or Email"
                  required
                  disabled={isOTPLogin && otpSent} // Disable email input after OTP is sent
                />
              </div>

              {(!isOTPLogin || isRegister) && (
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required minLength={3} />
                </div>
              )}

              {isRegister && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="pan">PAN Number</Label>
                    <Input id="pan" value={pan} onChange={(e) => setPan(e.target.value.toUpperCase())} placeholder="ABCDE1234F" required maxLength={10} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="mobile">Mobile Number</Label>
                    <Input id="mobile" value={mobile} onChange={(e) => setMobile(e.target.value)} placeholder="9876543210" required maxLength={15} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="arnNumber">ARN Number (Optional)</Label>
                    <Input id="arnNumber" value={arnNumber} onChange={(e) => setArnNumber(e.target.value)} placeholder="ARN-12345" />
                  </div>
                </>
              )}

              {isOTPLogin && otpSent && (
                <div className="space-y-2">
                  <Label htmlFor="otp">Enter OTP</Label>
                  <Input
                    id="otp"
                    type="text"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value)}
                    placeholder="Enter 6-digit OTP"
                    required
                    maxLength={6}
                    pattern="\d*"
                  />
                  <div className="flex justify-end">
                    <button type="button" onClick={() => setOtpSent(false)} className="text-xs text-primary hover:underline">
                        Change Username / Resend
                    </button>
                  </div>
                </div>
              )}

              <Button className="w-full gradient-primary border-0 text-white hover:opacity-90" size="lg" disabled={loading}>
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {isRegister ? "Create Account" : (isOTPLogin ? (otpSent ? "Verify & Login" : "Send OTP") : "Sign In")}
              </Button>
            </form>

            <div className="mt-4 text-center">
              {!isRegister && (
                <button type="button" onClick={toggleMode} className="text-sm text-primary hover:underline font-medium">
                  {isOTPLogin ? "Login with Password" : "Login with OTP"}
                </button>
              )}
            </div>

            <p className="text-center text-sm text-muted-foreground mt-4">
              {isRegister ? "Already have an account?" : "Don't have an account?"}{" "}
              <button onClick={() => { setIsRegister(!isRegister); setIsOTPLogin(false); }} className="text-primary font-medium hover:underline">
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
