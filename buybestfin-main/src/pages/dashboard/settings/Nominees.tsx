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
import { toast } from 'sonner';
import { Loader2, Plus, Trash2 } from 'lucide-react';

const nomineeSchema = z.object({
  name: z.string().min(2, "Nominee name is required"),
  relationship: z.string().min(2, "Relationship is required"),
  percentage: z.string().refine((val) => !isNaN(parseFloat(val)) && parseFloat(val) > 0 && parseFloat(val) <= 100, "Percentage must be between 1 and 100"),
  dob: z.string().optional(), // Can be optional? Ideally required for BSE.
  guardian_name: z.string().optional(),
});

type NomineeValues = z.infer<typeof nomineeSchema>;

interface Nominee {
  id: number;
  name: string;
  relationship: string;
  percentage: number;
}

const Nominees = () => {
  const [investorId, setInvestorId] = useState<number | null>(null);
  const [nominees, setNominees] = useState<Nominee[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<NomineeValues>({
    resolver: zodResolver(nomineeSchema),
    defaultValues: {
      name: '',
      relationship: '',
      percentage: '100',
    },
  });

  const fetchNominees = async (invId: number) => {
      try {
          const data: any = await api.get(`/api/investors/${invId}/nominees/`);
          setNominees(data.results || data);
      } catch (error) {
          console.error("Failed to load nominees", error);
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
            fetchNominees(profile.investor_id);
        } else {
            setLoading(false);
        }
      } catch (error) {
        setLoading(false);
      }
    };
    init();
  }, []);

  const onSubmit = async (data: NomineeValues) => {
    if (!investorId) return;
    setSubmitting(true);
    try {
      const payload = { ...data, percentage: parseFloat(data.percentage) };
      await api.post(`/api/investors/${investorId}/nominees/`, payload);
      toast.success("Nominee added successfully");
      setOpen(false);
      form.reset();
      fetchNominees(investorId);
    } catch (error: any) {
      toast.error(error.response?.data?.message || "Failed to add nominee");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
      if (!confirm("Are you sure you want to delete this nominee?")) return;
      try {
          await api.delete(`/api/nominees/${id}/`);
          toast.success("Nominee deleted");
          if (investorId) fetchNominees(investorId);
      } catch (error) {
          toast.error("Failed to delete nominee");
      }
  };

  if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin" /></div>;
  if (!investorId) return <div>You need to complete your investor profile first.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
            <h2 className="text-3xl font-bold tracking-tight">Nominees</h2>
            <p className="text-muted-foreground">Manage nominees for your investments.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button>
                    <Plus className="mr-2 h-4 w-4" /> Add Nominee
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Add Nominee</DialogTitle>
                    <DialogDescription>Enter nominee details.</DialogDescription>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                        <FormField
                            control={form.control}
                            name="name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Nominee Name</FormLabel>
                                    <FormControl>
                                        <Input {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <div className="grid grid-cols-2 gap-4">
                             <FormField
                                control={form.control}
                                name="relationship"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Relationship</FormLabel>
                                        <FormControl>
                                            <Input {...field} placeholder="e.g. Spouse, Son" />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                             <FormField
                                control={form.control}
                                name="percentage"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Allocation (%)</FormLabel>
                                        <FormControl>
                                            <Input {...field} type="number" max={100} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>
                         <FormField
                            control={form.control}
                            name="dob"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Date of Birth</FormLabel>
                                    <FormControl>
                                        <Input {...field} type="date" />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <Button type="submit" disabled={submitting} className="w-full">
                            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Add Nominee
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
                <TableHead>Name</TableHead>
                <TableHead>Relationship</TableHead>
                <TableHead>Allocation</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {nominees.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={4} className="text-center p-4">No nominees added.</TableCell>
                </TableRow>
              ) : (
                  nominees.map((n) => (
                    <TableRow key={n.id}>
                        <TableCell className="font-medium">{n.name}</TableCell>
                        <TableCell>{n.relationship}</TableCell>
                        <TableCell>{n.percentage}%</TableCell>
                        <TableCell className="text-right">
                             <Button variant="ghost" size="sm" onClick={() => handleDelete(n.id)}>
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

export default Nominees;
