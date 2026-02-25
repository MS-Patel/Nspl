import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

interface Mandate {
  id: number;
  mandate_id: string;
  amount_limit: number;
  start_date: string;
  end_date: string;
  status: string;
  status_display: string;
  bank_name: string;
  account_number: string;
  mandate_type: string;
}

const MandateList = () => {
  const [mandates, setMandates] = useState<Mandate[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchMandates = async () => {
    try {
      const response: any = await api.get('/api/mandates/');
      if (Array.isArray(response)) {
          setMandates(response);
      } else if (response.results) {
          setMandates(response.results);
      }
    } catch (error) {
      console.error('Failed to fetch mandates:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMandates();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return 'bg-green-500 hover:bg-green-600';
      case 'REJECTED':
        return 'bg-red-500 hover:bg-red-600';
      case 'PENDING':
        return 'bg-yellow-500 hover:bg-yellow-600';
      default:
        return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mandates</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Placeholder for Create Mandate Button - will be in Page component or separate form */}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Mandate ID</TableHead>
              <TableHead>Bank Account</TableHead>
              <TableHead className="text-right">Amount Limit</TableHead>
              <TableHead>Start Date</TableHead>
              <TableHead>End Date</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mandates.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={7} className="text-center">No mandates found.</TableCell>
                </TableRow>
            ) : (
                mandates.map((m) => (
                <TableRow key={m.id}>
                    <TableCell className="font-mono text-xs">{m.mandate_id}</TableCell>
                    <TableCell>
                        <div className="font-medium">{m.bank_name}</div>
                        <div className="text-xs text-muted-foreground">{m.account_number}</div>
                    </TableCell>
                    <TableCell className="text-right">₹{m.amount_limit}</TableCell>
                    <TableCell>{m.start_date}</TableCell>
                    <TableCell>{m.end_date || '-'}</TableCell>
                    <TableCell>{m.mandate_type === 'I' ? 'ISIP' : 'Physical'}</TableCell>
                    <TableCell>
                    <Badge className={getStatusColor(m.status)}>
                        {m.status_display}
                    </Badge>
                    </TableCell>
                </TableRow>
                ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default MandateList;
