import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Holding {
  id: number;
  scheme_name: string;
  amc: string;
  folio: string;
  units: number;
  average_cost: number;
  current_value: number;
  gain_loss: number;
}

const Holdings = () => {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHoldings = async () => {
      try {
        const response: any = await api.get('/api/holdings/');
        setHoldings(response);
      } catch (error) {
        console.error('Failed to fetch holdings:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHoldings();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(amount);
  };

  if (loading) return <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="space-y-6">
        <div>
            <h2 className="text-3xl font-bold tracking-tight">Portfolio Holdings</h2>
            <p className="text-muted-foreground">Detailed view of your current investments.</p>
        </div>
        <Card>
        <CardHeader>
            <CardTitle>All Holdings</CardTitle>
            <CardDescription>{holdings.length} Schemes found</CardDescription>
        </CardHeader>
        <CardContent>
            <Table>
            <TableHeader>
                <TableRow>
                <TableHead>Scheme</TableHead>
                <TableHead>AMC</TableHead>
                <TableHead>Folio</TableHead>
                <TableHead className="text-right">Units</TableHead>
                <TableHead className="text-right">Avg Cost</TableHead>
                <TableHead className="text-right">Current Value</TableHead>
                <TableHead className="text-right">Gain/Loss</TableHead>
                <TableHead className="text-right">Action</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {holdings.length === 0 ? (
                    <TableRow>
                        <TableCell colSpan={7} className="text-center">No holdings found.</TableCell>
                    </TableRow>
                ) : (
                    holdings.map((holding) => (
                    <TableRow key={holding.id}>
                        <TableCell className="font-medium">
                            <div className="max-w-[300px] truncate" title={holding.scheme_name}>{holding.scheme_name}</div>
                        </TableCell>
                        <TableCell>{holding.amc}</TableCell>
                        <TableCell className="font-mono text-xs">{holding.folio}</TableCell>
                        <TableCell className="text-right">{holding.units.toFixed(3)}</TableCell>
                        <TableCell className="text-right">{formatCurrency(holding.average_cost)}</TableCell>
                        <TableCell className="text-right font-bold">{formatCurrency(holding.current_value)}</TableCell>
                        <TableCell className={`text-right ${holding.gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {holding.gain_loss >= 0 ? '+' : ''}{formatCurrency(holding.gain_loss)}
                        </TableCell>
                        <TableCell className="text-right">
                             <Button size="sm" variant="outline" onClick={() => navigate(`/dashboard/investments/redeem/${holding.id}`)}>
                                Redeem
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

export default Holdings;
