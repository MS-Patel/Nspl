import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Loader2, KeyRound } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import logo from "@/assets/logo.png";
import { api } from "@/lib/api";

const OTPLogin = () => {
    const [step, setStep] = useState<'username' | 'otp'>('username');
    const [username, setUsername] = useState("");
    const [otp, setOtp] = useState("");
    const [loading, setLoading] = useState(false);
    const { toast } = useToast();

    const handleSendOTP = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!username) {
            toast({ title: "Error", description: "Please enter your username", variant: "destructive" });
            return;
        }

        setLoading(true);
        try {
            // Send OTP API
            const formData = new FormData();
            formData.append('username', username);

            // Using axios directly or api wrapper? api wrapper usually handles JSON.
            // Check api.ts implementation if possible, or assume it handles FormData if we pass it,
            // or we might need to send form-urlencoded or JSON.
            // View uses request.POST.get('username').
            // If API wrapper sends JSON, request.POST might be empty if not using JSON parser.
            // But SendOTPView is a View, not APIView. It likely expects form data.
            // Let's try sending standard object and see if API wrapper handles it as JSON.
            // But if it's a standard Django View, it might not read JSON body unless we parse it.
            // Wait, SendOTPView uses `request.POST.get`. That works for form-urlencoded.
            // APILoginView explicitly parses JSON body.
            // SendOTPView (lines 92) `request.POST.get('username')`.
            // So we should send form data.

            // To be safe with the `api` wrapper, let's see how it behaves.
            // Assuming `api.post` sends JSON by default.
            // If the backend view expects form data, we might need to send URLSearchParams.

            const params = new URLSearchParams();
            params.append('username', username);

            await api.post('/otp/send/', params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            toast({ title: "OTP Sent", description: "Please check your registered mobile number." });
            setStep('otp');
        } catch (error: any) {
            console.error("OTP Send error:", error);
            const message = error.response?.data?.message || "Failed to send OTP.";
            toast({ title: "Error", description: message, variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    const handleVerifyOTP = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!otp) {
            toast({ title: "Error", description: "Please enter the OTP", variant: "destructive" });
            return;
        }

        setLoading(true);
        try {
            const params = new URLSearchParams();
            params.append('username', username);
            params.append('otp', otp);

            const response = await api.post('/otp/login/', params, {
                 headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            if (response.status === 'success') {
                toast({ title: "Login Successful", description: "Redirecting..." });
                window.location.href = response.redirect_url || '/dashboard/admin/';
            } else {
                throw new Error(response.message || 'Login failed');
            }

        } catch (error: any) {
             console.error("OTP Verify error:", error);
             const message = error.response?.data?.message || "Invalid OTP.";
             toast({ title: "Error", description: message, variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
            {/* Background */}
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-secondary/10" />

            <div className="w-full max-w-md relative animate-fade-up">
                <Link to="/login" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
                    <ArrowLeft className="w-4 h-4" /> Back to Login
                </Link>

                <Card className="border-border/50 shadow-2xl backdrop-blur-sm bg-card/90">
                    <CardHeader className="text-center space-y-4">
                        <div className="mx-auto bg-primary/10 p-4 rounded-full">
                            <KeyRound className="w-8 h-8 text-primary" />
                        </div>
                        <div>
                            <CardTitle className="text-2xl">OTP Login</CardTitle>
                            <CardDescription className="mt-1">
                                {step === 'username' ? "Enter your username to receive OTP" : "Enter the OTP sent to your mobile"}
                            </CardDescription>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {step === 'username' ? (
                            <form onSubmit={handleSendOTP} className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="username">Username</Label>
                                    <Input
                                        id="username"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        placeholder="Enter your username"
                                        required
                                    />
                                </div>
                                <Button className="w-full gradient-primary border-0 text-white" size="lg" disabled={loading}>
                                    {loading && <Loader2 className="mr-2 w-4 h-4 animate-spin" />}
                                    Send OTP
                                </Button>
                            </form>
                        ) : (
                            <form onSubmit={handleVerifyOTP} className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="otp">Enter OTP</Label>
                                    <Input
                                        id="otp"
                                        value={otp}
                                        onChange={(e) => setOtp(e.target.value)}
                                        placeholder="Enter 6-digit OTP"
                                        maxLength={6}
                                        className="text-center letter-spacing-2 text-lg"
                                        required
                                    />
                                </div>
                                <Button className="w-full gradient-primary border-0 text-white" size="lg" disabled={loading}>
                                    {loading && <Loader2 className="mr-2 w-4 h-4 animate-spin" />}
                                    Verify & Login
                                </Button>
                                <div className="text-center">
                                    <button
                                        type="button"
                                        onClick={() => setStep('username')}
                                        className="text-sm text-muted-foreground hover:text-primary transition-colors"
                                    >
                                        Change Username
                                    </button>
                                </div>
                            </form>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default OTPLogin;
