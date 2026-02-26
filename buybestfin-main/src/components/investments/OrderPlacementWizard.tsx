import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

// --- Schemas ---

const baseSchema = z.object({
  investor_id: z.string().min(1, "Select an investor"),
  scheme_id: z.string().min(1, "Select a scheme"),
});

const lumpsumSchema = baseSchema.extend({
  transaction_type: z.literal('P'),
  amount: z.string().refine((val) => !isNaN(parseFloat(val)) && parseFloat(val) > 0, "Amount must be greater than 0"),
});

const sipSchema = baseSchema.extend({
  transaction_type: z.literal('SIP'),
  amount: z.string().refine((val) => !isNaN(parseFloat(val)) && parseFloat(val) > 0, "Amount must be greater than 0"),
  sip_frequency: z.enum(['MONTHLY', 'WEEKLY', 'DAILY', 'QUARTERLY']),
  sip_start_date: z.string().min(1, "Start date is required"),
  sip_installments: z.string().refine((val) => !isNaN(parseInt(val)) && parseInt(val) > 0, "Installments must be greater than 0"),
  mandate_id: z.string().min(1, "Select a mandate"),
});

const redeemSchema = baseSchema.extend({
  transaction_type: z.literal('R'),
  folio_number: z.string().min(1, "Select a folio"),
  units: z.string().optional(), // Can be amount or units
  amount: z.string().optional(),
  all_redeem: z.boolean().default(false),
}).refine((data) => data.units || data.amount || data.all_redeem, {
    message: "Specify amount, units, or check 'Redeem All'",
    path: ["amount"],
});

const switchSchema = baseSchema.extend({
  transaction_type: z.literal('S'),
  folio_number: z.string().min(1, "Select a source folio"),
  target_scheme_id: z.string().min(1, "Select a target scheme"),
  units: z.string().optional(),
  amount: z.string().optional(),
  all_redeem: z.boolean().default(false),
}).refine((data) => data.units || data.amount || data.all_redeem, {
    message: "Specify amount, units, or check 'Switch All'",
    path: ["amount"],
});

// Union Schema for Form
const formSchema = z.union([lumpsumSchema, sipSchema, redeemSchema, switchSchema]);

// --- Types ---
type FormValues = z.infer<typeof formSchema>;

interface Scheme {
  id: number;
  name: string;
  scheme_code: string;
  min_purchase_amount: number;
  is_sip_allowed: boolean;
}

interface Investor {
  id: number;
  user__username: string;
  pan: string;
  name: string; // Assuming name is available or derived
}

interface Mandate {
    id: number;
    mandate_id: string;
    amount_limit: number;
    bank_account__bank_name: string;
}

interface Folio {
    folio_number: string;
    scheme__id: number;
    scheme__name: string;
    current_value: number;
    units: number;
}

interface OrderPlacementWizardProps {
  initialTab?: string;
  initialValues?: Partial<FormValues>;
}

const OrderPlacementWizard = ({ initialTab = "lumpsum", initialValues }: OrderPlacementWizardProps) => {
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [folios, setFolios] = useState<Folio[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(initialTab);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      transaction_type: 'P',
      amount: '',
      units: '',
      sip_frequency: 'MONTHLY',
      sip_installments: '12',
      all_redeem: false,
    },
  });

  const { watch, setValue, reset, control } = form;

  useEffect(() => {
    if (initialValues) {
        // Merge defaults with initial values
        const defaults = {
            transaction_type: 'P',
            amount: '',
            units: '',
            sip_frequency: 'MONTHLY',
            sip_installments: '12',
            all_redeem: false,
        };
        reset({ ...defaults, ...initialValues });

        // Set Tab based on transaction_type
        if (initialValues.transaction_type === 'R') setActiveTab('redeem');
        else if (initialValues.transaction_type === 'SIP') setActiveTab('sip');
        else if (initialValues.transaction_type === 'S') setActiveTab('switch');
        else if (initialValues.transaction_type === 'P') setActiveTab('lumpsum');
    }
  }, [initialValues, reset]);
  const selectedInvestor = watch('investor_id');
  const selectedScheme = watch('scheme_id');

  // --- Data Fetching ---

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const data: any = await api.get('/api/metadata/?fetch_schemes=true');
        if (data.schemes) setSchemes(data.schemes);
        if (data.investors) setInvestors(data.investors);
      } catch (error) {
        console.error("Failed to load metadata", error);
        toast.error("Failed to load schemes/investors");
      }
    };
    fetchMetadata();
  }, []);

  useEffect(() => {
    if (selectedInvestor) {
      const fetchInvestorData = async () => {
        try {
          const data: any = await api.get(`/api/metadata/?investor_id=${selectedInvestor}`);
          if (data.mandates) setMandates(data.mandates);

          try {
              const holdings: any = await api.get(`/api/holdings/?investor_id=${selectedInvestor}`);
              setFolios(holdings.map((h: any) => ({
                  folio_number: h.folio,
                  scheme__id: h.scheme_id,
                  scheme__name: h.scheme_name,
                  units: h.units,
                  current_value: h.current_value
              })));
          } catch(e) {
              console.error("Failed to fetch holdings", e);
          }

        } catch (e) {
          console.error(e);
        }
      };
      fetchInvestorData();
    } else {
        setMandates([]);
        setFolios([]);
    }
  }, [selectedInvestor]);

  // --- Handlers ---

  const onTabChange = (value: string) => {
    setActiveTab(value);
    // Reset relevant fields or set transaction type
    if (value === 'lumpsum') setValue('transaction_type', 'P');
    else if (value === 'sip') setValue('transaction_type', 'SIP');
    else if (value === 'redeem') setValue('transaction_type', 'R');
    else if (value === 'switch') setValue('transaction_type', 'S');
  };

  const onSubmit = async (data: FormValues) => {
    setLoading(true);
    try {
      const payload: any = { ...data };

      // Numeric Conversions
      if (payload.amount) payload.amount = parseFloat(payload.amount);
      if (payload.units) payload.units = parseFloat(payload.units);
      if (payload.sip_installments) payload.sip_installments = parseInt(payload.sip_installments);

      const response: any = await api.post('/api/orders/create/', payload);

      if (response.status === 'success') {
        toast.success(response.message || "Order Placed Successfully");
        reset({
            investor_id: selectedInvestor, // Keep investor selected
            transaction_type: data.transaction_type,
            amount: '',
            units: '',
            all_redeem: false,
            sip_installments: '12',
            sip_frequency: 'MONTHLY'
        });
      } else {
        toast.error(response.message || "Order Failed");
      }
    } catch (error: any) {
      toast.error(error.response?.data?.message || error.message || "Submission Failed");
      if (error.response?.data?.detail) {
          // Field errors?
          console.error(error.response.data);
      }
    } finally {
      setLoading(false);
    }
  };

  // --- Filtering ---
  // Filter schemes based on transaction type (e.g., SIP allowed)
  const filteredSchemes = schemes.filter(s => {
      if (activeTab === 'sip') return s.is_sip_allowed;
      return true;
  });

  // Filter folios based on selected scheme (for Redeem/Switch if scheme is selected first? Usually for Redeem we select Folio first or Scheme first?
  // Let's assume user selects Scheme -> Folio, or Folio -> Scheme.
  // Ideally for Redeem, we show a list of current holdings.
  // But strictly following the wizard approach:
  const filteredFolios = folios.filter(f => {
      if (selectedScheme) return f.scheme__id.toString() === selectedScheme;
      return true;
  });

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>New Investment</CardTitle>
          <CardDescription>Place orders for Purchase, SIP, Redemption, or Switch.</CardDescription>
        </CardHeader>
        <CardContent>
            <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

                {/* Investor Selection */}
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

                <Tabs value={activeTab} onValueChange={onTabChange} className="w-full">
                    <TabsList className="grid w-full grid-cols-4">
                        <TabsTrigger value="lumpsum">Lumpsum</TabsTrigger>
                        <TabsTrigger value="sip">SIP</TabsTrigger>
                        <TabsTrigger value="redeem">Redeem</TabsTrigger>
                        <TabsTrigger value="switch">Switch</TabsTrigger>
                    </TabsList>

                    {/* Common Scheme Selection (except Redeem might be different) */}
                    <div className="mt-4">
                        <FormField
                            control={control}
                            name="scheme_id"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Scheme</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select Scheme" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {filteredSchemes.slice(0, 100).map((s) => (
                                                <SelectItem key={s.id} value={s.id.toString()}>
                                                    {s.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <TabsContent value="lumpsum" className="space-y-4">
                         <FormField
                            control={control}
                            name="amount"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Amount (₹)</FormLabel>
                                    <FormControl>
                                        <Input type="number" placeholder="Min 1000" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </TabsContent>

                    <TabsContent value="sip" className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <FormField
                                control={control}
                                name="amount"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>SIP Amount (₹)</FormLabel>
                                        <FormControl>
                                            <Input type="number" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                             <FormField
                                control={control}
                                name="sip_frequency"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Frequency</FormLabel>
                                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="MONTHLY">Monthly</SelectItem>
                                                <SelectItem value="WEEKLY">Weekly</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                             <FormField
                                control={control}
                                name="sip_start_date"
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
                                name="sip_installments"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Installments</FormLabel>
                                        <FormControl>
                                            <Input type="number" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>
                         <FormField
                            control={control}
                            name="mandate_id"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Mandate</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select Mandate" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {mandates.map((m) => (
                                                <SelectItem key={m.id} value={m.id.toString()}>
                                                    {m.mandate_id} - ₹{m.amount_limit} ({m.bank_account__bank_name})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </TabsContent>

                    <TabsContent value="redeem" className="space-y-4">
                         <FormField
                            control={control}
                            name="folio_number"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Folio</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select Folio" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {filteredFolios.map((f) => (
                                                <SelectItem key={f.folio_number} value={f.folio_number}>
                                                    {f.folio_number} (Units: {f.units})
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
                            name="all_redeem"
                            render={({ field }) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                    <FormControl>
                                        <input type="checkbox" checked={field.value} onChange={field.onChange} />
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Redeem All Units</FormLabel>
                                    </div>
                                </FormItem>
                            )}
                        />
                         {!watch('all_redeem') && (
                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={control}
                                    name="amount"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Amount (₹)</FormLabel>
                                            <FormControl>
                                                <Input type="number" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={control}
                                    name="units"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Units</FormLabel>
                                            <FormControl>
                                                <Input type="number" step="0.001" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>
                         )}
                    </TabsContent>

                    <TabsContent value="switch" className="space-y-4">
                         <FormField
                            control={control}
                            name="folio_number"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Source Folio</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select Folio" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {filteredFolios.map((f) => (
                                                <SelectItem key={f.folio_number} value={f.folio_number}>
                                                    {f.folio_number} (Units: {f.units})
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
                            name="target_scheme_id"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Target Scheme</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select Target Scheme" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {schemes.slice(0, 100).map((s) => (
                                                <SelectItem key={s.id} value={s.id.toString()}>
                                                    {s.name}
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
                            name="all_redeem"
                            render={({ field }) => (
                                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                                    <FormControl>
                                        <input type="checkbox" checked={field.value} onChange={field.onChange} />
                                    </FormControl>
                                    <div className="space-y-1 leading-none">
                                        <FormLabel>Switch All Units</FormLabel>
                                    </div>
                                </FormItem>
                            )}
                        />
                         {!watch('all_redeem') && (
                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={control}
                                    name="amount"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Amount (₹)</FormLabel>
                                            <FormControl>
                                                <Input type="number" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={control}
                                    name="units"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Units</FormLabel>
                                            <FormControl>
                                                <Input type="number" step="0.001" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>
                         )}
                    </TabsContent>

                </Tabs>

                <Button type="submit" disabled={loading} className="w-full">
                    {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {activeTab === 'lumpsum' && 'Place Lumpsum Order'}
                    {activeTab === 'sip' && 'Register SIP'}
                    {activeTab === 'redeem' && 'Redeem Funds'}
                    {activeTab === 'switch' && 'Switch Funds'}
                </Button>

            </form>
            </Form>
        </CardContent>
      </Card>
    </div>
  );
};

export default OrderPlacementWizard;
