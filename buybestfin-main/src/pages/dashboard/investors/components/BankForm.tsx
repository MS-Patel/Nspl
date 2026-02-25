import { useState } from 'react';
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
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2 } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

const bankSchema = z.object({
  bank_name: z.string().min(2, 'Bank name is required'),
  account_number: z.string().min(5, 'Account number is required'),
  ifsc_code: z.string().length(11, 'IFSC Code must be 11 characters').regex(/^[A-Z]{4}0[A-Z0-9]{6}$/, 'Invalid IFSC format'),
  account_type: z.enum(['SB', 'CB', 'NE', 'NO']),
  branch_name: z.string().optional(),
  is_default: z.boolean().default(false),
});

type BankFormValues = z.infer<typeof bankSchema>;

interface BankFormProps {
  investorId: number;
  onSuccess: () => void;
  onCancel: () => void;
}

const BankForm = ({ investorId, onSuccess, onCancel }: BankFormProps) => {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const form = useForm<BankFormValues>({
    resolver: zodResolver(bankSchema),
    defaultValues: {
      bank_name: '',
      account_number: '',
      ifsc_code: '',
      account_type: 'SB',
      branch_name: '',
      is_default: false,
    },
  });

  const onSubmit = async (values: BankFormValues) => {
    setLoading(true);
    try {
      await api.post(`/api/investors/${investorId}/bank-accounts/`, values);
      toast({ title: "Success", description: "Bank account added successfully." });
      onSuccess();
    } catch (error: any) {
      console.error("Failed to add bank account", error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to add bank account.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="bank_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Bank Name</FormLabel>
              <FormControl>
                <Input placeholder="HDFC Bank" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid grid-cols-2 gap-4">
            <FormField
            control={form.control}
            name="account_number"
            render={({ field }) => (
                <FormItem>
                <FormLabel>Account Number</FormLabel>
                <FormControl>
                    <Input placeholder="1234567890" {...field} />
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
                    <Input placeholder="HDFC0001234" {...field} onChange={e => field.onChange(e.target.value.toUpperCase())} />
                </FormControl>
                <FormMessage />
                </FormItem>
            )}
            />
        </div>
        <div className="grid grid-cols-2 gap-4">
            <FormField
            control={form.control}
            name="account_type"
            render={({ field }) => (
                <FormItem>
                <FormLabel>Account Type</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                    <SelectTrigger>
                        <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                    <SelectItem value="SB">Savings</SelectItem>
                    <SelectItem value="CB">Current</SelectItem>
                    <SelectItem value="NE">NRE</SelectItem>
                    <SelectItem value="NO">NRO</SelectItem>
                    </SelectContent>
                </Select>
                <FormMessage />
                </FormItem>
            )}
            />
             <FormField
                control={form.control}
                name="branch_name"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Branch Name (Optional)</FormLabel>
                    <FormControl>
                        <Input placeholder="Mumbai Main" {...field} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
            />
        </div>

        <FormField
          control={form.control}
          name="is_default"
          render={({ field }) => (
            <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
              <FormControl>
                <Checkbox
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
              <div className="space-y-1 leading-none">
                <FormLabel>
                  Set as Default
                </FormLabel>
              </div>
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
            <Button type="submit" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Add Bank Account
            </Button>
        </div>
      </form>
    </Form>
  );
};

export default BankForm;
