import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft, ArrowRight, Check, Save } from 'lucide-react';
import { Separator } from '@/components/ui/separator';

// --- SCHEMAS ---

const personalSchema = z.object({
    firstname: z.string().min(2, "First name is required"),
    middlename: z.string().optional(),
    lastname: z.string().min(2, "Last name is required"),
    email: z.string().email("Invalid email"),
    mobile: z.string().min(10, "Mobile number must be at least 10 digits"),
    pan: z.string().length(10, "PAN must be 10 characters").regex(/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/, "Invalid PAN format"),
    dob: z.string().optional(),
    gender: z.string().optional(),
    occupation: z.string().optional(),
    tax_status: z.string().optional(),
    holding_nature: z.string().optional(),
});

const bankSchema = z.object({
    account_number: z.string().min(1, "Account Number is required"),
    ifsc_code: z.string().length(11, "IFSC Code must be 11 characters"),
    bank_name: z.string().optional(),
    account_type: z.string().default('SB'),
});

const fatcaSchema = z.object({
    place_of_birth: z.string().optional(),
    country_of_birth: z.string().optional(),
    source_of_wealth: z.string().optional(),
    income_slab: z.string().optional(),
    pep_status: z.string().optional(),
});

const nomineeSchema = z.object({
    name: z.string().min(1, "Nominee Name is required"),
    relationship: z.string().min(1, "Relationship is required"),
    percentage: z.string().refine((val) => !isNaN(parseFloat(val)) && parseFloat(val) > 0 && parseFloat(val) <= 100, "Percentage must be between 1 and 100"),
    date_of_birth: z.string().optional(),
});

// --- MAIN COMPONENT ---

const OnboardingWizard = () => {
    const [step, setStep] = useState(1);
    const [investorId, setInvestorId] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);
    const { toast } = useToast();
    const navigate = useNavigate();

    // --- FORMS ---
    const personalForm = useForm<z.infer<typeof personalSchema>>({
        resolver: zodResolver(personalSchema),
        defaultValues: {
            gender: 'M', occupation: '02', tax_status: '01', holding_nature: 'SI'
        }
    });

    const bankForm = useForm<z.infer<typeof bankSchema>>({
        resolver: zodResolver(bankSchema),
        defaultValues: { account_type: 'SB' }
    });

    const fatcaForm = useForm<z.infer<typeof fatcaSchema>>({
        resolver: zodResolver(fatcaSchema),
        defaultValues: {
             place_of_birth: 'India', country_of_birth: 'India', source_of_wealth: '01', income_slab: '32', pep_status: 'N'
        }
    });

    const nomineeForm = useForm<z.infer<typeof nomineeSchema>>({
        resolver: zodResolver(nomineeSchema),
        defaultValues: { percentage: '100', relationship: 'Spouse' }
    });

    // --- HANDLERS ---

    const handlePersonalSubmit = async (data: z.infer<typeof personalSchema>) => {
        setLoading(true);
        try {
            let response;
            if (investorId) {
                // Update existing (Though typically step 1 is creation)
                // Using PATCH on detail endpoint
                 response = await api.patch(`/api/investors/${investorId}/`, data);
                 toast({ title: "Updated", description: "Personal details updated." });
            } else {
                // Create New
                response = await api.post('/api/investors/onboard/', data);
                setInvestorId(response.id);
                toast({ title: "Created", description: "Investor profile created." });
            }
            setStep(2);
        } catch (error: any) {
            console.error(error);
            const msg = error.response?.data?.message || "Failed to save personal details.";
            let desc = msg;
            if (error.response?.data?.errors) {
                 desc = JSON.stringify(error.response.data.errors);
            }
            toast({ title: "Error", description: desc, variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    const handleBankSubmit = async (data: z.infer<typeof bankSchema>) => {
        if (!investorId) return;
        setLoading(true);
        try {
            await api.post(`/api/investors/${investorId}/bank-accounts/`, {
                ...data,
                is_default: true
            });
            toast({ title: "Saved", description: "Bank account added." });
            setStep(4);
        } catch (error: any) {
            console.error(error);
            toast({ title: "Error", description: "Failed to save bank details.", variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    const handleFATCASubmit = async (data: z.infer<typeof fatcaSchema>) => {
        if (!investorId) return;
        setLoading(true);
        try {
            await api.patch(`/api/investors/${investorId}/`, data);
            toast({ title: "Saved", description: "FATCA details updated." });
            setStep(5);
        } catch (error: any) {
            console.error(error);
            toast({ title: "Error", description: "Failed to save FATCA details.", variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    const handleNomineeSubmit = async (data: z.infer<typeof nomineeSchema>) => {
        if (!investorId) return;
        setLoading(true);
        try {
            await api.post(`/api/investors/${investorId}/nominees/`, {
                ...data,
                percentage: parseFloat(data.percentage)
            });
            toast({ title: "Saved", description: "Nominee added." });
            setStep(6);
        } catch (error: any) {
             console.error(error);
             toast({ title: "Error", description: "Failed to save nominee.", variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    const handleDocumentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!investorId || !e.target.files?.length) return;
        const file = e.target.files[0];
        setLoading(true);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('document_type', 'OTHERS'); // Default, maybe add selector later
        formData.append('description', 'Uploaded via Wizard');

        try {
            // Need to handle multipart/form-data.
            // api wrapper sets json by default. We must override.
            // But api wrapper might not allow easy override if it force sets header.
            // Actually Axios allows override.

            // NOTE: api.ts wrapper sets 'Content-Type': 'application/json' in defaults.
            // If we pass headers in config, they merge.
            // But we need to UNSET Content-Type to let browser set boundary.
            // Axios handles this if we pass FormData, BUT only if Content-Type is NOT set to something else explicitly.
            // In `src/lib/api.ts`, it is set in defaults.
            // We can try setting it to undefined.

            await api.post(`/api/investors/${investorId}/documents/`, formData, {
                headers: {
                    'Content-Type': undefined
                }
            });

            toast({ title: "Uploaded", description: "Document uploaded successfully." });
        } catch (error: any) {
             console.error(error);
             toast({ title: "Error", description: "Failed to upload document.", variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    const handleKYCCheck = async () => {
        if (!investorId) return;
        setLoading(true);
        try {
             // For now just toggle or verify. Requirement says "Integrate ToggleKYC".
             // We'll use the toggle endpoint for simulation.
             await api.post(`/api/investors/${investorId}/toggle-kyc/`);
             toast({ title: "Verified", description: "KYC Status updated." });
             setStep(3);
        } catch (error: any) {
             toast({ title: "Error", description: "Failed to verify KYC.", variant: "destructive" });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8 p-4">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Onboard Investor</h1>
                <p className="text-muted-foreground">Follow the steps to create a new investor profile.</p>
            </div>

            {/* Stepper */}
            <div className="flex items-center space-x-2 md:space-x-4 mb-8 overflow-x-auto pb-4">
                {[1, 2, 3, 4, 5, 6].map((s) => (
                    <div key={s} className="flex items-center min-w-fit">
                        <div className={`
                            flex items-center justify-center w-8 h-8 rounded-full border-2 text-sm font-medium
                            ${step === s ? 'border-primary bg-primary text-white' :
                              step > s ? 'border-primary bg-primary text-white' : 'border-muted-foreground text-muted-foreground'}
                        `}>
                            {step > s ? <Check className="w-4 h-4" /> : s}
                        </div>
                        <span className={`ml-2 text-sm hidden md:block ${step === s ? 'font-bold text-primary' : 'text-muted-foreground'}`}>
                            {s === 1 && "Personal"}
                            {s === 2 && "KYC"}
                            {s === 3 && "Bank"}
                            {s === 4 && "FATCA"}
                            {s === 5 && "Nominee"}
                            {s === 6 && "Docs"}
                        </span>
                        {s < 6 && <div className={`w-4 md:w-12 h-1 mx-2 ${step > s ? 'bg-primary' : 'bg-muted'}`} />}
                    </div>
                ))}
            </div>

            <Card className="min-h-[400px]">
                <CardHeader>
                    <CardTitle>
                        {step === 1 && "Personal Details"}
                        {step === 2 && "KYC Verification"}
                        {step === 3 && "Bank Details"}
                        {step === 4 && "FATCA / Tax Details"}
                        {step === 5 && "Nominee Details"}
                        {step === 6 && "Document Upload"}
                    </CardTitle>
                    <CardDescription>
                       Step {step} of 6
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {step === 1 && (
                        <form id="personal-form" onSubmit={personalForm.handleSubmit(handlePersonalSubmit)} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>First Name *</Label>
                                    <Input {...personalForm.register('firstname')} />
                                    {personalForm.formState.errors.firstname && <p className="text-destructive text-xs">{personalForm.formState.errors.firstname.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>Middle Name</Label>
                                    <Input {...personalForm.register('middlename')} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Last Name *</Label>
                                    <Input {...personalForm.register('lastname')} />
                                    {personalForm.formState.errors.lastname && <p className="text-destructive text-xs">{personalForm.formState.errors.lastname.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>Email *</Label>
                                    <Input {...personalForm.register('email')} type="email" />
                                    {personalForm.formState.errors.email && <p className="text-destructive text-xs">{personalForm.formState.errors.email.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>Mobile *</Label>
                                    <Input {...personalForm.register('mobile')} />
                                    {personalForm.formState.errors.mobile && <p className="text-destructive text-xs">{personalForm.formState.errors.mobile.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>PAN *</Label>
                                    <Input {...personalForm.register('pan')} className="uppercase" maxLength={10} />
                                    {personalForm.formState.errors.pan && <p className="text-destructive text-xs">{personalForm.formState.errors.pan.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>Date of Birth</Label>
                                    <Input {...personalForm.register('dob')} type="date" />
                                </div>
                            </div>
                        </form>
                    )}

                    {step === 2 && (
                        <div className="flex flex-col items-center justify-center space-y-4 py-8">
                            <div className="bg-muted p-6 rounded-full">
                                <Check className="w-12 h-12 text-primary" />
                            </div>
                            <h3 className="text-xl font-semibold">Perform KYC Check</h3>
                            <p className="text-muted-foreground text-center max-w-md">
                                Verify the investor's KYC status with the central registry.
                            </p>
                            <Button onClick={handleKYCCheck} disabled={loading}>
                                {loading && <Loader2 className="mr-2 w-4 h-4 animate-spin" />}
                                Check & Verify KYC
                            </Button>
                        </div>
                    )}

                    {step === 3 && (
                        <form id="bank-form" onSubmit={bankForm.handleSubmit(handleBankSubmit)} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>Account Number *</Label>
                                    <Input {...bankForm.register('account_number')} />
                                    {bankForm.formState.errors.account_number && <p className="text-destructive text-xs">{bankForm.formState.errors.account_number.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>IFSC Code *</Label>
                                    <Input {...bankForm.register('ifsc_code')} className="uppercase" maxLength={11} />
                                    {bankForm.formState.errors.ifsc_code && <p className="text-destructive text-xs">{bankForm.formState.errors.ifsc_code.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>Bank Name</Label>
                                    <Input {...bankForm.register('bank_name')} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Account Type</Label>
                                    <Select onValueChange={(val) => bankForm.setValue('account_type', val)} defaultValue={bankForm.getValues('account_type')}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select Type" />
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
                        </form>
                    )}

                    {step === 4 && (
                        <form id="fatca-form" onSubmit={fatcaForm.handleSubmit(handleFATCASubmit)} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>Place of Birth</Label>
                                    <Input {...fatcaForm.register('place_of_birth')} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Country of Birth</Label>
                                    <Input {...fatcaForm.register('country_of_birth')} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Source of Wealth</Label>
                                    <Select onValueChange={(val) => fatcaForm.setValue('source_of_wealth', val)} defaultValue={fatcaForm.getValues('source_of_wealth')}>
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="01">Salary</SelectItem>
                                            <SelectItem value="02">Business</SelectItem>
                                            <SelectItem value="03">Gift</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Income Slab</Label>
                                    <Select onValueChange={(val) => fatcaForm.setValue('income_slab', val)} defaultValue={fatcaForm.getValues('income_slab')}>
                                        <SelectTrigger><SelectValue /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="31">Below 1 Lakh</SelectItem>
                                            <SelectItem value="32">1-5 Lakhs</SelectItem>
                                            <SelectItem value="33">5-10 Lakhs</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </form>
                    )}

                    {step === 5 && (
                        <form id="nominee-form" onSubmit={nomineeForm.handleSubmit(handleNomineeSubmit)} className="space-y-4">
                             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>Nominee Name *</Label>
                                    <Input {...nomineeForm.register('name')} />
                                    {nomineeForm.formState.errors.name && <p className="text-destructive text-xs">{nomineeForm.formState.errors.name.message}</p>}
                                </div>
                                <div className="space-y-2">
                                    <Label>Relationship *</Label>
                                    <Input {...nomineeForm.register('relationship')} />
                                </div>
                                <div className="space-y-2">
                                    <Label>Date of Birth</Label>
                                    <Input {...nomineeForm.register('date_of_birth')} type="date" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Percentage %</Label>
                                    <Input {...nomineeForm.register('percentage')} type="number" />
                                </div>
                            </div>
                        </form>
                    )}

                    {step === 6 && (
                        <div className="space-y-6">
                            <div className="border-2 border-dashed rounded-lg p-8 text-center hover:bg-muted/50 transition-colors">
                                <div className="flex flex-col items-center gap-2">
                                    <div className="p-4 rounded-full bg-muted">
                                        <Save className="w-8 h-8 text-muted-foreground" />
                                    </div>
                                    <h3 className="font-semibold">Upload Documents</h3>
                                    <p className="text-sm text-muted-foreground">Support for PDF, JPG, PNG</p>
                                    <Input type="file" className="max-w-xs mt-4" onChange={handleDocumentUpload} />
                                </div>
                            </div>

                            <Separator />

                            <div className="flex justify-center">
                                <Button onClick={() => navigate('/dashboard/investors')} variant="outline" size="lg">
                                    Complete & Go to Dashboard
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
                <CardFooter className="flex justify-between">
                    <Button variant="ghost" onClick={() => setStep(prev => Math.max(1, prev - 1))} disabled={step === 1 || loading}>
                        <ArrowLeft className="mr-2 h-4 w-4" /> Back
                    </Button>

                    {step === 1 && (
                        <Button form="personal-form" type="submit" disabled={loading}>
                            {investorId ? "Update & Next" : "Create & Next"} {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
                        </Button>
                    )}
                    {step === 2 && (
                        <Button variant="outline" onClick={() => setStep(3)}>Skip / Next <ArrowRight className="ml-2 h-4 w-4" /></Button>
                    )}
                    {step === 3 && (
                        <Button form="bank-form" type="submit" disabled={loading}>
                             Save & Next {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
                        </Button>
                    )}
                    {step === 4 && (
                        <Button form="fatca-form" type="submit" disabled={loading}>
                             Save & Next {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
                        </Button>
                    )}
                    {step === 5 && (
                        <Button form="nominee-form" type="submit" disabled={loading}>
                             Save & Next {loading && <Loader2 className="ml-2 h-4 w-4 animate-spin" />}
                        </Button>
                    )}
                </CardFooter>
            </Card>
        </div>
    );
};

export default OnboardingWizard;
