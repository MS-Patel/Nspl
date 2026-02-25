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
import { Loader2 } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

const nomineeSchema = z.object({
  name: z.string().min(2, 'Name is required'),
  relationship: z.string().min(1, 'Relationship is required'),
  percentage: z.number().min(1).max(100),
  dob: z.string().optional(),
  guardian_name: z.string().optional(),
  guardian_pan: z.string().optional(),
  pan: z.string().optional(),
  mobile: z.string().optional(),
  email: z.string().email().optional().or(z.literal('')),
  address_1: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  pincode: z.string().optional(),
  country: z.string().default('India'),
});

type NomineeFormValues = z.infer<typeof nomineeSchema>;

interface NomineeFormProps {
  investorId: number;
  onSuccess: () => void;
  onCancel: () => void;
}

const NomineeForm = ({ investorId, onSuccess, onCancel }: NomineeFormProps) => {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const form = useForm<NomineeFormValues>({
    resolver: zodResolver(nomineeSchema),
    defaultValues: {
      name: '',
      relationship: '',
      percentage: 100,
      dob: '',
      guardian_name: '',
      guardian_pan: '',
      pan: '',
      mobile: '',
      email: '',
      address_1: '',
      city: '',
      state: '',
      pincode: '',
      country: 'India',
    },
  });

  const onSubmit = async (values: NomineeFormValues) => {
    setLoading(true);
    try {
      // Clean empty strings to null/undefined if needed, or backend handles it?
      // Zod handles optional().or(literal(''))
      await api.post(`/api/investors/${investorId}/nominees/`, values);
      toast({ title: "Success", description: "Nominee added successfully." });
      onSuccess();
    } catch (error: any) {
      console.error("Failed to add nominee", error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to add nominee.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
            <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
                <FormItem>
                <FormLabel>Nominee Name</FormLabel>
                <FormControl>
                    <Input placeholder="Jane Doe" {...field} />
                </FormControl>
                <FormMessage />
                </FormItem>
            )}
            />
            <FormField
            control={form.control}
            name="relationship"
            render={({ field }) => (
                <FormItem>
                <FormLabel>Relationship</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                    <SelectTrigger>
                        <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                        <SelectItem value="Spouse">Spouse</SelectItem>
                        <SelectItem value="Father">Father</SelectItem>
                        <SelectItem value="Mother">Mother</SelectItem>
                        <SelectItem value="Son">Son</SelectItem>
                        <SelectItem value="Daughter">Daughter</SelectItem>
                        <SelectItem value="Others">Others</SelectItem>
                    </SelectContent>
                </Select>
                <FormMessage />
                </FormItem>
            )}
            />
        </div>

        <div className="grid grid-cols-2 gap-4">
             <FormField
                control={form.control}
                name="percentage"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Percentage (%)</FormLabel>
                    <FormControl>
                        <Input type="number" {...field} onChange={e => field.onChange(parseFloat(e.target.value))} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
            />
             <FormField
                control={form.control}
                name="dob"
                render={({ field }) => (
                    <FormItem>
                    <FormLabel>Date of Birth</FormLabel>
                    <FormControl>
                        <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                    </FormItem>
                )}
            />
        </div>

        <div className="grid grid-cols-2 gap-4">
            <FormField
            control={form.control}
            name="guardian_name"
            render={({ field }) => (
                <FormItem>
                <FormLabel>Guardian Name (If Minor)</FormLabel>
                <FormControl>
                    <Input placeholder="" {...field} />
                </FormControl>
                <FormMessage />
                </FormItem>
            )}
            />
             <FormField
            control={form.control}
            name="guardian_pan"
            render={({ field }) => (
                <FormItem>
                <FormLabel>Guardian PAN</FormLabel>
                <FormControl>
                    <Input placeholder="" {...field} />
                </FormControl>
                <FormMessage />
                </FormItem>
            )}
            />
        </div>

        <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
            <Button type="submit" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Add Nominee
            </Button>
        </div>
      </form>
    </Form>
  );
};

export default NomineeForm;
