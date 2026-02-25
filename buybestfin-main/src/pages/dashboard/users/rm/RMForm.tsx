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
import { RM, Branch } from '@/types/users';

const rmSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  username: z.string().min(3, 'Username must be at least 3 characters'),
  password: z.string().optional().or(z.literal('')), // Optional for edit
  employee_code: z.string().min(1, 'Employee code is required'),
  branch: z.string().optional(), // Select returns string
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
  bank_name: z.string().optional(),
  account_number: z.string().optional(),
  ifsc_code: z.string().optional(),
});

type RMFormValues = z.infer<typeof rmSchema>;

const RMForm = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [branches, setBranches] = useState<Branch[]>([]);
  const isEditMode = !!id;

  const form = useForm<RMFormValues>({
    resolver: zodResolver(rmSchema),
    defaultValues: {
      name: '',
      email: '',
      username: '',
      password: '',
      employee_code: '',
      branch: '',
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
      bank_name: '',
      account_number: '',
      ifsc_code: '',
    },
  });

  useEffect(() => {
    const fetchBranches = async () => {
      try {
        const result = await api.get<Branch[]>('/api/branches/'); // Assuming this endpoint returns list directly or paginated
        // If paginated, need to handle results. For now assuming list or handling generic
        if (Array.isArray(result)) {
            setBranches(result);
        } else if ('results' in (result as any)) {
            setBranches((result as any).results);
        }
      } catch (error) {
        console.error("Failed to fetch branches", error);
      }
    };
    fetchBranches();

    if (isEditMode) {
      const fetchRM = async () => {
        setLoading(true);
        try {
          const data = await api.get<RM>(`/api/rms/${id}/`);
          form.reset({
            name: data.name,
            email: data.email,
            username: data.username,
            employee_code: data.employee_code,
            branch: data.branch ? data.branch.toString() : '',
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
            bank_name: data.bank_name || '',
            account_number: data.account_number || '',
            ifsc_code: data.ifsc_code || '',
            password: '', // Don't fill password
          });
        } catch (error) {
          console.error("Failed to fetch RM", error);
          toast({
            title: "Error",
            description: "Failed to load RM details.",
            variant: "destructive",
          });
          navigate('/dashboard/users/rm');
        } finally {
          setLoading(false);
        }
      };
      fetchRM();
    }
  }, [id, isEditMode, form, toast, navigate]);

  const onSubmit = async (values: RMFormValues) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        branch: values.branch ? parseInt(values.branch) : null,
      };

      // Remove password if empty in edit mode
      if (isEditMode && !payload.password) {
        delete (payload as any).password;
      }

      // Clean up empty optional fields to avoid backend issues if any
      Object.keys(payload).forEach(key => {
          if ((payload as any)[key] === '') {
              (payload as any)[key] = null;
          }
      });

      if (isEditMode) {
        await api.patch(`/api/rms/${id}/`, payload);
        toast({ title: "Success", description: "RM updated successfully." });
      } else {
        if (!payload.password) {
             toast({ title: "Error", description: "Password is required for new users.", variant: "destructive" });
             setLoading(false);
             return;
        }
        await api.post('/api/rms/', payload);
        toast({ title: "Success", description: "RM created successfully." });
      }
      navigate('/dashboard/users/rm');
    } catch (error: any) {
      console.error("Submit failed", error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save RM.",
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
        <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard/users/rm')}>
            <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
            <h1 className="text-3xl font-bold tracking-tight">{isEditMode ? 'Edit RM' : 'Create New RM'}</h1>
            <p className="text-muted-foreground">Fill in the details below.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
            <CardTitle>Personal & Professional Details</CardTitle>
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
                                        <Input placeholder="John Doe" {...field} />
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
                                        <Input placeholder="john@example.com" {...field} />
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
                                        <Input placeholder="johndoe" {...field} />
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
                            name="employee_code"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Employee Code *</FormLabel>
                                    <FormControl>
                                        <Input placeholder="EMP001" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="branch"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Branch</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select a branch" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            {branches.map(branch => (
                                                <SelectItem key={branch.id} value={branch.id.toString()}>
                                                    {branch.name} ({branch.code})
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
                        {isEditMode ? 'Update RM' : 'Create RM'}
                    </Button>
                </form>
            </Form>
        </CardContent>
      </Card>
    </div>
  );
};

export default RMForm;
