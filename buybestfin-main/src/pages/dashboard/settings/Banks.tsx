import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { Loader2, Plus, Trash2 } from 'lucide-react';

const bankSchema = z.object({
  bank_name: z.string().min(2, "Bank name is required"),
  account_number: z.string().min(5, "Account number is required"),
  ifsc_code: z.string().length(11, "IFSC Code must be 11 characters"),
  account_type: z.enum(['SAVINGS', 'CURRENT', 'NRE', 'NRO']),
  is_default: z.boolean().optional(),
});

type BankValues = z.infer<typeof bankSchema>;

interface BankAccount {
  id: number;
  bank_name: string;
  account_number: string;
  ifsc_code: string;
  account_type: string;
  is_default: boolean;
}

const Banks = () => {
  const [investorId, setInvestorId] = useState<number | null>(null);
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<BankValues>({
    resolver: zodResolver(bankSchema),
    defaultValues: {
      bank_name: '',
      account_number: '',
      ifsc_code: '',
      account_type: 'SAVINGS',
      is_default: false,
    },
  });

  const fetchAccounts = async (invId: number) => {
      try {
          const data: any = await api.get(`/api/investors/${invId}/bank-accounts/`);
          setAccounts(data.results || data);
      } catch (error) {
          console.error("Failed to load bank accounts", error);
      } finally {
          setLoading(false);
      }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const profile: any = await api.get('/api/user/profile/');
        if (profile.investor_id) {
            setInvestorId(profile.investor_id);
            fetchAccounts(profile.investor_id);
        } else {
            setLoading(false); // Not an investor
        }
      } catch (error) {
        setLoading(false);
      }
    };
    init();
  }, []);

  const onSubmit = async (data: BankValues) => {
    if (!investorId) return;
    setSubmitting(true);
    try {
      await api.post(`/api/investors/${investorId}/bank-accounts/`, data);
      toast.success("Bank account added successfully");
      setOpen(false);
      form.reset();
      fetchAccounts(investorId);
    } catch (error: any) {
      toast.error(error.response?.data?.message || "Failed to add bank account");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
      if (!confirm("Are you sure you want to delete this bank account?")) return;
      try {
          // Assuming DELETE endpoint exists at /api/bank-accounts/:id/
          await api.delete(`/api/bank-accounts/${id}/`);
          toast.success("Bank account deleted");
          if (investorId) fetchAccounts(investorId);
      } catch (error) {
          toast.error("Failed to delete account");
      }
  };

  if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>;

  if (!investorId) return <div>You need to complete your investor profile first.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
            <h2 className="text-3xl font-bold tracking-tight">Bank Accounts</h2>
            <p className="text-muted-foreground">Manage your linked bank accounts.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button>
                    <Plus className="mr-2 h-4 w-4" /> Add Bank Account
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Add Bank Account</DialogTitle>
                    <DialogDescription>Enter your bank details.</DialogDescription>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={form.control}
                            name="bank_name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Bank Name</FormLabel>
                                    <FormControl>
                                        <Input {...field} placeholder="HDFC Bank" />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="account_number"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Account Number</FormLabel>
                                    <FormControl>
                                        <Input {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="ifsc_code"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>IFSC Code</FormLabel>
                                    <FormControl>
                                        <Input {...field} maxLength={11} className="uppercase" />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                         <FormField
                            control={form.control}
                            name="account_type"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Account Type</FormLabel>
                                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="SAVINGS">Savings</SelectItem>
                                            <SelectItem value="CURRENT">Current</SelectItem>
                                            <SelectItem value="NRE">NRE</SelectItem>
                                            <SelectItem value="NRO">NRO</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <Button type="submit" disabled={submitting} className="w-full">
                            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Add Account
                        </Button>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Bank Name</TableHead>
                <TableHead>Account Number</TableHead>
                <TableHead>IFSC</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={5} className="text-center p-4">No bank accounts added.</TableCell>
                </TableRow>
              ) : (
                  accounts.map((acc) => (
                    <TableRow key={acc.id}>
                        <TableCell className="font-medium">
                            {acc.bank_name}
                            {acc.is_default && <span className="ml-2 text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">Default</span>}
                        </TableCell>
                        <TableCell className="font-mono">{acc.account_number}</TableCell>
                        <TableCell className="font-mono">{acc.ifsc_code}</TableCell>
                        <TableCell>{acc.account_type}</TableCell>
                        <TableCell className="text-right">
                             <Button variant="ghost" size="sm" onClick={() => handleDelete(acc.id)}>
                                <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                        </TableCell>
                    </TableRow>
                  ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default Banks;
