import { useState, useEffect } from 'react';
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
import { Download, FileDown, Loader2 } from 'lucide-react';

interface BrokerageImport {
  id: number;
  month: number;
  year: number;
  uploaded_at: string;
  status: string;
  total_brokerage: number;
}

const Reports = () => {
  const [reports, setReports] = useState<BrokerageImport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const data: any = await api.get('/api/reports/');
        setReports(data.results || data);
      } catch (error) {
        console.error("Failed to load reports", error);
      } finally {
        setLoading(false);
      }
    };
    fetchReports();
  }, []);

  const getMonthName = (month: number) => {
    return new Date(0, month - 1).toLocaleString('default', { month: 'long' });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  if (loading) return <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Brokerage Reports</h2>
        <p className="text-muted-foreground">Download payout and transaction reports.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Available Reports</CardTitle>
          <CardDescription>Monthly brokerage imports</CardDescription>
        </CardHeader>
        <CardContent>
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Month/Year</TableHead>
                        <TableHead>Total Brokerage</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {reports.length === 0 ? (
                        <TableRow><TableCell colSpan={4} className="text-center">No reports available.</TableCell></TableRow>
                    ) : (
                        reports.map((report) => (
                            <TableRow key={report.id}>
                                <TableCell className="font-medium">{getMonthName(report.month)} {report.year}</TableCell>
                                <TableCell>{formatCurrency(report.total_brokerage)}</TableCell>
                                <TableCell>
                                    <Badge variant={report.status === 'COMPLETED' ? 'default' : 'secondary'}>
                                        {report.status}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-right space-x-2">
                                    <Button size="sm" variant="outline" asChild>
                                        <a href={`/payouts/import/${report.id}/export/`} target="_blank" rel="noreferrer">
                                            <Download className="mr-2 h-4 w-4" /> Payout
                                        </a>
                                    </Button>
                                    <Button size="sm" variant="outline" asChild>
                                        <a href={`/payouts/import/${report.id}/export-amc/`} target="_blank" rel="noreferrer">
                                            <FileDown className="mr-2 h-4 w-4" /> AMC
                                        </a>
                                    </Button>
                                    <Button size="sm" variant="outline" asChild>
                                        <a href={`/payouts/import/${report.id}/export-transactions/`} target="_blank" rel="noreferrer">
                                            <FileDown className="mr-2 h-4 w-4" /> Txn
                                        </a>
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

export default Reports;
