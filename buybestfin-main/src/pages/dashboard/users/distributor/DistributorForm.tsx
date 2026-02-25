import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/use-toast';
import { Loader2, ArrowLeft } from 'lucide-react';
import { Distributor, RM } from '@/types/users';

const distributorSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().optional().or(z.literal('')),
  arn_number: z.string().optional(),
  rm: z.string().optional(), // RM ID as string
  parent: z.string().optional(), // Parent Distributor ID as string
  mobile: z.string().optional(),
  alternate_mobile: z.string().optional(),
  alternate_email: z.string().email('Invalid email').optional().or(z.literal('')),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  pincode: z.string().optional(),
  country: z.string().default('India'),
  dob: z.string().optional(),
  gstin: z.string().optional(),
  pan: z.string().optional(),
  bank_name: z.string().optional(),
  account_number: z.string().optional(),
  ifsc_code: z.string().optional(),
});

type DistributorFormValues = z.infer<typeof distributorSchema>;

const DistributorForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [rms, setRMs] = useState<RM[]>([]);
  const isEditMode = !!id;

  const form = useForm<DistributorFormValues>({
    resolver: zodResolver(distributorSchema),
    defaultValues: {
      name: '',
      email: '',
      username: '',
      password: '',
      arn_number: '',
      rm: '',
      parent: '',
      mobile: '',
      alternate_mobile: '',
      alternate_email: '',
      address: '',
      city: '',
      state: '',
      pincode: '',
      country: 'India',
      dob: '',
      gstin: '',
      pan: '',
      bank_name: '',
      account_number: '',
      ifsc_code: '',
    },
  });

  useEffect(() => {
    const fetchDropdowns = async () => {
      try {
        // Fetch RMs
        const rmResult = await api.get<{ results: RM[] }>('/api/rms/?page_size=100');
        if (rmResult && rmResult.results) {
            setRMs(rmResult.results);
        }
      } catch (error) {
        console.error("Failed to fetch dropdown data", error);
      }
    };
    fetchDropdowns();

    if (isEditMode) {
      const fetchDistributor = async () => {
        setLoading(true);
        try {
          const data = await api.get<Distributor>(`/api/distributors/${id}/`);
          form.reset({
            name: data.name,
            email: data.email,
            username: data.username,
            arn_number: data.arn_number || '',
            rm: data.rm ? data.rm.toString() : '',
            parent: data.parent ? data.parent.toString() : '',
            mobile: data.mobile || '',
            alternate_mobile: data.alternate_mobile || '',
            alternate_email: data.alternate_email || '',
            address: data.address || '',
            city: data.city || '',
            state: data.state || '',
            pincode: data.pincode || '',
            country: data.country || 'India',
            dob: data.dob || '',
            gstin: data.gstin || '',
            pan: data.pan || '',
            bank_name: data.bank_name || '',
            account_number: data.account_number || '',
            ifsc_code: data.ifsc_code || '',
            password: '',
          });
        } catch (error) {
          console.error("Failed to fetch Distributor", error);
          toast({
            title: "Error",
            description: "Failed to load Distributor details.",
            variant: "destructive",
          });
          navigate('/dashboard/users/distributor');
        } finally {
          setLoading(false);
        }
      };
      fetchDistributor();
    }
  }, [id, isEditMode, form, toast, navigate]);

  const onSubmit = async (values: DistributorFormValues) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        rm: values.rm ? parseInt(values.rm) : null,
        parent: values.parent ? parseInt(values.parent) : null,
      };

      if (isEditMode && !payload.password) {
        delete (payload as any).password;
      }

      Object.keys(payload).forEach(key => {
          if ((payload as any)[key] === '') {
              (payload as any)[key] = null;
          }
      });

      if (isEditMode) {
        await api.patch(`/api/distributors/${id}/`, payload);
        toast({ title: "Success", description: "Distributor updated successfully." });
      } else {
        if (!payload.password) {
             toast({ title: "Error", description: "Password is required for new users.", variant: "destructive" });
             setLoading(false);
             return;
        }
        await api.post('/api/distributors/', payload);
        toast({ title: "Success", description: "Distributor created successfully." });
      }
      navigate('/dashboard/users/distributor');
    } catch (error: any) {
      console.error("Submit failed", error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save Distributor.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading && isEditMode) {
    return <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  }

  return (
    <div className="flex flex-col gap-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard/users/distributor')}>
            <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
            <h1 className="text-3xl font-bold tracking-tight">{isEditMode ? 'Edit Distributor' : 'Create New Distributor'}</h1>
            <p className="text-muted-foreground">Fill in the details below.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
            <CardTitle>Distributor Details</CardTitle>
        </CardHeader>
        <CardContent>
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FormField
                            control={form.control}
                            name="name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Full Name *</FormLabel>
                                    <FormControl>
                                        <Input placeholder="Jane Smith" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                         <FormField
                            control={form.control}
                            name="email"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Email *</FormLabel>
                                    <FormControl>
                                        <Input placeholder="jane@example.com" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                         <FormField
                            control={form.control}
                            name="username"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Username (Login ID) *</FormLabel>
                                    <FormControl>
                                        <Input placeholder="janesmith" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                         <FormField
                            control={form.control}
                            name="password"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Password {isEditMode ? '(Leave blank to keep current)' : '*'}</FormLabel>
                                    <FormControl>
                                        <Input type="password" placeholder="********" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                         <FormField
                            control={form.control}
                            name="arn_number"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>ARN Number</FormLabel>
                                    <FormControl>
                                        <Input placeholder="ARN-XXXX" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="rm"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Assigned RM</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select an RM" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {rms.map(rm => (
                                                <SelectItem key={rm.id} value={rm.id.toString()}>
                                                    {rm.name} ({rm.employee_code})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="mobile"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Mobile</FormLabel>
                                    <FormControl>
                                        <Input placeholder="9876543210" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="gstin"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>GSTIN</FormLabel>
                                    <FormControl>
                                        <Input placeholder="" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="pan"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>PAN</FormLabel>
                                    <FormControl>
                                        <Input placeholder="" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <FormField
                            control={form.control}
                            name="city"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>City</FormLabel>
                                    <FormControl>
                                        <Input placeholder="" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="state"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>State</FormLabel>
                                    <FormControl>
                                        <Input placeholder="" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="pincode"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Pincode</FormLabel>
                                    <FormControl>
                                        <Input placeholder="" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <FormField
                            control={form.control}
                            name="address"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Address</FormLabel>
                                    <FormControl>
                                        <Input placeholder="" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />

                    <Button type="submit" disabled={loading}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {isEditMode ? 'Update Distributor' : 'Create Distributor'}
                    </Button>
                </form>
            </Form>
        </CardContent>
      </Card>
    </div>
  );
};

export default DistributorForm;
