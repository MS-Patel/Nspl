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

interface SIP {
  id: number;
  created_at: string;
  investor_name: string;
  scheme_name: string;
  amount: number;
  frequency_display: string;
  start_date: string;
  end_date: string | null;
  installments: number;
  status: string;
  status_display: string;
  bse_reg_no: string;
}

const SIPList = () => {
  const [sips, setSips] = useState<SIP[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSIPs = async () => {
    try {
      const response: any = await api.get('/api/sips/');
      if (Array.isArray(response)) {
          setSips(response);
      } else if (response.results) {
          setSips(response.results);
      }
    } catch (error) {
      console.error('Failed to fetch SIPs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSIPs();
  }, []);

  const handleCancelSIP = async (id: number) => {
      if (!confirm("Are you sure you want to cancel this SIP?")) return;

      try {
          await api.post(`/api/sips/${id}/cancel/`);
          toast.success("SIP Cancelled Successfully");
          fetchSIPs();
      } catch (error: any) {
          toast.error("Failed to cancel SIP: " + (error.response?.data?.message || "Unknown Error"));
      }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-green-500 hover:bg-green-600';
      case 'CANCELLED':
      case 'REJECTED':
        return 'bg-red-500 hover:bg-red-600';
      case 'PAUSED':
        return 'bg-yellow-500 hover:bg-yellow-600';
      default:
        return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  if (loading) return <div>Loading SIPs...</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>SIP Book</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Start Date</TableHead>
              <TableHead>Reg No</TableHead>
              <TableHead>Investor</TableHead>
              <TableHead>Scheme</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Frequency</TableHead>
              <TableHead>Installments</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sips.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={9} className="text-center">No active SIPs found.</TableCell>
                </TableRow>
            ) : (
                sips.map((sip) => (
                <TableRow key={sip.id}>
                    <TableCell>{new Date(sip.start_date).toLocaleDateString()}</TableCell>
                    <TableCell className="font-mono text-xs">{sip.bse_reg_no || '-'}</TableCell>
                    <TableCell>{sip.investor_name}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={sip.scheme_name}>{sip.scheme_name}</TableCell>
                    <TableCell className="text-right">₹{sip.amount}</TableCell>
                    <TableCell>{sip.frequency_display}</TableCell>
                    <TableCell>{sip.installments}</TableCell>
                    <TableCell>
                    <Badge className={getStatusColor(sip.status)}>
                        {sip.status_display}
                    </Badge>
                    </TableCell>
                    <TableCell>
                        {sip.status === 'ACTIVE' && (
                            <Button variant="destructive" size="sm" onClick={() => handleCancelSIP(sip.id)}>
                                Cancel
                            </Button>
                        )}
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

export default SIPList;
