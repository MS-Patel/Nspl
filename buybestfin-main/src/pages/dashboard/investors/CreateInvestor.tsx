import { useState } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft, ArrowRight, Check } from 'lucide-react';

const CreateInvestor = () => {
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const { toast } = useToast();
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        // Step 1: Personal
        firstname: '',
        middlename: '',
        lastname: '',
        email: '',
        mobile: '',
        pan: '',
        dob: '',

        // Step 2: Bank
        account_number: '',
        ifsc_code: '',
        bank_name: '',
        account_type: 'SB',

        // Step 3: Nominee
        nominee_name: '',
        nominee_relation: '',
        nominee_dob: '',
        nominee_percent: '100',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSelectChange = (name: string, value: string) => {
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const validateStep = (currentStep: number) => {
        if (currentStep === 1) {
            if (!formData.firstname || !formData.lastname || !formData.email || !formData.mobile || !formData.pan) {
                toast({
                    title: "Validation Error",
                    description: "Please fill all required fields.",
                    variant: "destructive"
                });
                return false;
            }
        }
        return true;
    };

    const handleNext = () => {
        if (validateStep(step)) {
            setStep(prev => prev + 1);
        }
    };

    const handleBack = () => {
        setStep(prev => prev - 1);
    };

    const handleSubmit = async () => {
        if (!validateStep(step)) return;

        setLoading(true);
        try {
            // Construct payload for nested serializer
            const payload = {
                firstname: formData.firstname,
                middlename: formData.middlename,
                lastname: formData.lastname,
                email: formData.email,
                mobile: formData.mobile,
                pan: formData.pan,
                dob: formData.dob || null, // Convert empty string to null
                bank_accounts: [{
                    account_number: formData.account_number,
                    ifsc_code: formData.ifsc_code,
                    bank_name: formData.bank_name,
                    account_type: formData.account_type,
                    is_default: true
                }],
                nominees: [{
                    name: formData.nominee_name,
                    relationship: formData.nominee_relation,
                    date_of_birth: formData.nominee_dob || null, // Convert empty string to null
                    percentage: parseFloat(formData.nominee_percent)
                }]
            };

            await api.post('/api/investors/onboard/', payload);

            toast({
                title: "Success",
                description: "Investor Profile Created Successfully",
            });
            navigate('/dashboard/investors');
        } catch (error: any) {
            console.error(error);
             const message = error.response?.data?.message || "Failed to create investor.";
             // Handle nested errors if possible
             let description = message;
             if (error.response?.data?.errors) {
                 description = JSON.stringify(error.response.data.errors);
             }

            toast({
                title: "Error",
                description: description,
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Onboard Investor</h1>
                <p className="text-muted-foreground">Follow the steps to create a new investor profile.</p>
            </div>

            {/* Stepper */}
            <div className="flex items-center space-x-4 mb-8">
                {[1, 2, 3, 4].map((s) => (
                    <div key={s} className="flex items-center">
                        <div className={`
                            flex items-center justify-center w-8 h-8 rounded-full border-2
                            ${step === s ? 'border-primary bg-primary text-white' :
                              step > s ? 'border-primary bg-primary text-white' : 'border-muted-foreground text-muted-foreground'}
                        `}>
                            {step > s ? <Check className="w-4 h-4" /> : s}
                        </div>
                        {s < 4 && <div className={`w-12 h-1 mx-2 ${step > s ? 'bg-primary' : 'bg-muted'}`} />}
                    </div>
                ))}
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>
                        {step === 1 && "Personal Details"}
                        {step === 2 && "Bank Details"}
                        {step === 3 && "Nominee Details"}
                        {step === 4 && "Review & Submit"}
                    </CardTitle>
                    <CardDescription>
                        {step === 1 && "Enter basic information and PAN."}
                        {step === 2 && "Add primary bank account."}
                        {step === 3 && "Add nominee information."}
                        {step === 4 && "Review details and upload documents (optional)."}
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {step === 1 && (
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="firstname">First Name *</Label>
                                <Input id="firstname" name="firstname" value={formData.firstname} onChange={handleChange} required />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="middlename">Middle Name</Label>
                                <Input id="middlename" name="middlename" value={formData.middlename} onChange={handleChange} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="lastname">Last Name *</Label>
                                <Input id="lastname" name="lastname" value={formData.lastname} onChange={handleChange} required />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="email">Email *</Label>
                                <Input id="email" name="email" type="email" value={formData.email} onChange={handleChange} required />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="mobile">Mobile *</Label>
                                <Input id="mobile" name="mobile" value={formData.mobile} onChange={handleChange} required />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="pan">PAN *</Label>
                                <Input id="pan" name="pan" value={formData.pan} onChange={handleChange} required maxLength={10} className="uppercase" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="dob">Date of Birth</Label>
                                <Input id="dob" name="dob" type="date" value={formData.dob} onChange={handleChange} />
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="account_number">Account Number *</Label>
                                    <Input id="account_number" name="account_number" value={formData.account_number} onChange={handleChange} required />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="ifsc_code">IFSC Code *</Label>
                                    <Input id="ifsc_code" name="ifsc_code" value={formData.ifsc_code} onChange={handleChange} required className="uppercase" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="bank_name">Bank Name</Label>
                                    <Input id="bank_name" name="bank_name" value={formData.bank_name} onChange={handleChange} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="account_type">Account Type</Label>
                                    <Select value={formData.account_type} onValueChange={(val) => handleSelectChange('account_type', val)}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select type" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="SB">Savings</SelectItem>
                                            <SelectItem value="CB">Current</SelectItem>
                                            <SelectItem value="NRE">NRE</SelectItem>
                                            <SelectItem value="NRO">NRO</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="nominee_name">Nominee Name</Label>
                                    <Input id="nominee_name" name="nominee_name" value={formData.nominee_name} onChange={handleChange} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="nominee_relation">Relationship</Label>
                                    <Input id="nominee_relation" name="nominee_relation" value={formData.nominee_relation} onChange={handleChange} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="nominee_dob">Date of Birth</Label>
                                    <Input id="nominee_dob" name="nominee_dob" type="date" value={formData.nominee_dob} onChange={handleChange} />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="nominee_percent">Percentage</Label>
                                    <Input id="nominee_percent" name="nominee_percent" type="number" value={formData.nominee_percent} onChange={handleChange} />
                                </div>
                            </div>
                        </div>
                    )}

                    {step === 4 && (
                        <div className="space-y-4">
                            <div className="bg-muted p-4 rounded-md">
                                <h3 className="font-semibold mb-2">Summary</h3>
                                <p><strong>Name:</strong> {formData.firstname} {formData.lastname}</p>
                                <p><strong>Email:</strong> {formData.email}</p>
                                <p><strong>PAN:</strong> {formData.pan}</p>
                                <p><strong>Bank:</strong> {formData.bank_name} ({formData.account_number})</p>
                                <p><strong>Nominee:</strong> {formData.nominee_name} ({formData.nominee_relation})</p>
                            </div>
                            <div className="space-y-2">
                                <Label>Document Upload (Optional)</Label>
                                <div className="border-2 border-dashed rounded-md p-8 text-center text-muted-foreground">
                                    <p>Drag and drop files here or click to upload.</p>
                                    <Input type="file" className="hidden" />
                                </div>
                            </div>
                        </div>
                    )}
                </CardContent>
                <CardFooter className="flex justify-between">
                    <Button variant="outline" onClick={handleBack} disabled={step === 1}>
                        <ArrowLeft className="mr-2 h-4 w-4" /> Back
                    </Button>
                    {step < 4 ? (
                        <Button onClick={handleNext}>
                            Next <ArrowRight className="ml-2 h-4 w-4" />
                        </Button>
                    ) : (
                        <Button onClick={handleSubmit} disabled={loading}>
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Submit
                        </Button>
                    )}
                </CardFooter>
            </Card>
        </div>
    );
};

export default CreateInvestor;
