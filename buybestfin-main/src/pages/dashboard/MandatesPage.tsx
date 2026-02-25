import { useState } from 'react';
import MandateList from '@/components/investments/MandateList';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { api } from '@/lib/api';
import { toast } from 'sonner';

const MandatesPage = () => {
    const [isCreating, setIsCreating] = useState(false);

    return (
        <div className="flex flex-col gap-8">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Mandates</h1>
                    <p className="text-muted-foreground">Manage your bank mandates for SIPs.</p>
                </div>
                <Button onClick={() => setIsCreating(!isCreating)}>
                    {isCreating ? "Cancel" : "Create New Mandate"}
                </Button>
            </div>

            {isCreating && <CreateMandateForm onClose={() => setIsCreating(false)} />}

            <MandateList />
        </div>
    );
};

const CreateMandateForm = ({ onClose }: { onClose: () => void }) => {
    const [loading, setLoading] = useState(false);
    const [amountLimit, setAmountLimit] = useState('100000');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

    // In a real implementation, we would fetch investors and bank accounts if the user is an Admin/RM
    // For now, let's assume Investor context or hardcode input for simplicity of the "Create" UI demo
    // We need at least an investor ID to proceed.
    // For this demo, let's assume we are the investor or picking 'self'.

    const handleSubmit = async () => {
        setLoading(true);
        try {
            // Fetch User/Investor Context first or assume
            // This part requires selecting an Investor and Bank Account.
            // Since we don't have that context easily in this isolated component without prop drilling or context,
            // let's show a toast that this feature requires selecting a Bank Account.

            // To make it functional, we would need to fetch `api/metadata` to get bank accounts.
            toast.error("Please select a valid Bank Account (Not implemented in this simple view)");

        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="w-full max-w-md mx-auto mb-8 border-primary/20 bg-primary/5">
            <CardHeader>
                <CardTitle>Register New Mandate</CardTitle>
                <CardDescription>Create an E-Mandate for automatic payments.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-1">
                    <Label>Amount Limit</Label>
                    <Input type="number" value={amountLimit} onChange={(e) => setAmountLimit(e.target.value)} />
                </div>
                <div className="space-y-1">
                    <Label>Start Date</Label>
                    <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                </div>
                 <div className="space-y-1">
                    <Label>End Date</Label>
                    <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                </div>
            </CardContent>
            <CardFooter>
                 <Button onClick={handleSubmit} disabled={loading} className="w-full">
                    {loading ? "Processing..." : "Submit to BSE"}
                </Button>
            </CardFooter>
        </Card>
    )
}

export default MandatesPage;
