import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { toast } from 'sonner';
import { Loader2, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const mandateSchema = z.object({
  investor_id: z.string().min(1, "Select an investor"),
  bank_account_id: z.string().min(1, "Select a bank account"),
  amount_limit: z.string().refine((val) => !isNaN(parseFloat(val)) && parseFloat(val) > 0, "Amount must be greater than 0"),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().optional(),
  mandate_type: z.enum(['I', 'X']), // I = ISIP (E-Mandate), X = Physical
});

type FormValues = z.infer<typeof mandateSchema>;

interface Investor {
  id: number;
  user__username: string;
  pan: string;
  name: string;
}

interface BankAccount {
  id: number;
  bank_name: string;
  account_number: string;
}

const CreateMandate = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [isInvestorRole, setIsInvestorRole] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(mandateSchema),
    defaultValues: {
      amount_limit: '100000',
      mandate_type: 'I',
      start_date: new Date().toISOString().split('T')[0],
      end_date: '2099-12-31',
    },
  });

  const { watch, setValue, control } = form;
  const selectedInvestor = watch('investor_id');

  useEffect(() => {
    const init = async () => {
      try {
        const user: any = await api.get('/api/user/me/');
        if (user.role === 'INVESTOR' && user.investor_id) {
            setIsInvestorRole(true);
            setValue('investor_id', user.investor_id.toString());
        } else {
            // Fetch investors for dropdown
            const data: any = await api.get('/api/metadata/');
            if (data.investors) setInvestors(data.investors);
        }
      } catch (error) {
        console.error("Initialization failed", error);
        toast.error("Failed to load user data");
      }
    };
    init();
  }, [setValue]);

  useEffect(() => {
    if (selectedInvestor) {
      const fetchBanks = async () => {
        try {
          // Check if we can use the nested endpoint
          const banks: any = await api.get(`/api/investors/${selectedInvestor}/bank-accounts/`);
          // It might return paginated result or list. Based on API View it is ListCreateAPIView which usually returns pagination if configured.
          // StandardResultsSetPagination is used. So it returns { count: ..., results: [...] }
          if (banks.results) setBankAccounts(banks.results);
          else if (Array.isArray(banks)) setBankAccounts(banks);
        } catch (error) {
          console.error("Failed to fetch bank accounts", error);
          toast.error("Failed to fetch bank accounts");
        }
      };
      fetchBanks();
    } else {
        setBankAccounts([]);
    }
  }, [selectedInvestor]);

  const onSubmit = async (data: FormValues) => {
    setLoading(true);
    try {
      const payload = {
          ...data,
          amount_limit: parseFloat(data.amount_limit),
          bank_account_id: parseInt(data.bank_account_id),
          investor_id: parseInt(data.investor_id)
      };

      const response: any = await api.post('/api/mandates/create/', payload);

      if (response.status === 'success') {
        toast.success(response.message || "Mandate Created");
        if (response.auth_url) {
             window.location.href = response.auth_url;
        } else {
             navigate('/dashboard/investments/mandates');
        }
      } else {
        toast.error(response.message || "Mandate Creation Failed");
      }
    } catch (error: any) {
      console.error(error);
      toast.error(error.response?.data?.message || "Submission Failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
       <div className="flex items-center space-x-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard/investments/mandates')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h2 className="text-3xl font-bold tracking-tight">Create New Mandate</h2>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Mandate Registration</CardTitle>
          <CardDescription>Register a new bank mandate for SIPs.</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

                {/* Investor Selection (only if not investor) */}
                {!isInvestorRole && (
                    <FormField
                        control={control}
                        name="investor_id"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Investor</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                    <FormControl>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select Investor" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        {investors.map((inv) => (
                                            <SelectItem key={inv.id} value={inv.id.toString()}>
                                                {inv.name || inv.user__username} ({inv.pan})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                )}

                <FormField
                    control={control}
                    name="bank_account_id"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Bank Account</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select Bank Account" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    {bankAccounts.map((bank) => (
                                        <SelectItem key={bank.id} value={bank.id.toString()}>
                                            {bank.bank_name} - {bank.account_number}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={control}
                    name="amount_limit"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Amount Limit (₹)</FormLabel>
                            <FormControl>
                                <Input type="number" {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={control}
                        name="start_date"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>Start Date</FormLabel>
                                <FormControl>
                                    <Input type="date" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={control}
                        name="end_date"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>End Date</FormLabel>
                                <FormControl>
                                    <Input type="date" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>

                 <FormField
                    control={control}
                    name="mandate_type"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>Mandate Type</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    <SelectItem value="I">E-Mandate (ISIP)</SelectItem>
                                    <SelectItem value="X">Physical (XSIP)</SelectItem>
                                </SelectContent>
                            </Select>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <Button type="submit" disabled={loading} className="w-full">
                    {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Create & Authorize
                </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};

export default CreateMandate;
