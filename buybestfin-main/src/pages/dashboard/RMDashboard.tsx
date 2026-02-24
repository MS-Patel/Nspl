import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Users, Briefcase, IndianRupee } from 'lucide-react';

interface RMDashboardData {
  distributor_count: number;
  investor_count: number;
  total_aum: number;
  recent_orders: Array<{
    id: number;
    unique_ref_no: string;
    investor_name: string;
    scheme_name: string;
    amount: number;
    status_display: string;
    created_at: string;
  }>;
}

const RMDashboard = () => {
  const [data, setData] = useState<RMDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await api.get('/api/dashboard/rm/');
        setData(result);
      } catch (error) {
        console.error('Error fetching rm dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="p-8">Loading dashboard...</div>;
  }

  if (!data) {
    return <div className="p-8 text-red-500">Failed to load dashboard data.</div>;
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">RM Dashboard</h1>
        <p className="text-muted-foreground">Overview of your distributors and investors.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total AUM</CardTitle>
            <IndianRupee className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(data.total_aum)}</div>
            <p className="text-xs text-muted-foreground">Assets Under Management</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Distributors</CardTitle>
            <Briefcase className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.distributor_count}</div>
            <p className="text-xs text-muted-foreground">Linked Distributors</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Investors</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.investor_count}</div>
            <p className="text-xs text-muted-foreground">Total Investors</p>
          </CardContent>
        </Card>
      </div>

      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Recent Orders</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ref No</TableHead>
                <TableHead>Investor</TableHead>
                <TableHead>Scheme</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.recent_orders.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={6} className="text-center">No recent orders found.</TableCell>
                </TableRow>
              ) : (
                data.recent_orders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-medium">{order.unique_ref_no}</TableCell>
                    <TableCell>{order.investor_name}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={order.scheme_name}>
                      {order.scheme_name}
                    </TableCell>
                    <TableCell>{formatCurrency(order.amount)}</TableCell>
                    <TableCell>{order.status_display}</TableCell>
                    <TableCell className="text-right">{formatDate(order.created_at)}</TableCell>
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

export default RMDashboard;
