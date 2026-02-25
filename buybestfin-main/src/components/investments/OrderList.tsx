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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Order {
  id: number;
  unique_ref_no: string;
  created_at: string;
  investor_name: string;
  scheme_name: string;
  transaction_type_display: string;
  amount: number;
  units: number;
  status: string;
  status_display: string;
  bse_remarks: string;
}

const OrderList = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const response: any = await api.get('/api/orders/');
        // The API returns a paginated response by default if pagination is enabled in DRF settings.
        // If not, it returns a list. Let's assume list or handle both.
        if (Array.isArray(response)) {
            setOrders(response);
        } else if (response.results) {
            setOrders(response.results);
        }
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'APPROVED':
      case 'ALLOTTED':
        return 'bg-green-500 hover:bg-green-600';
      case 'REJECTED':
        return 'bg-red-500 hover:bg-red-600';
      case 'PENDING':
      case 'SENT_TO_BSE':
        return 'bg-yellow-500 hover:bg-yellow-600';
      default:
        return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  if (loading) return <div>Loading orders...</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Order History</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Ref No</TableHead>
              <TableHead>Investor</TableHead>
              <TableHead>Scheme</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead className="text-right">Units</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Remarks</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={9} className="text-center">No orders found.</TableCell>
                </TableRow>
            ) : (
                orders.map((order) => (
                <TableRow key={order.id}>
                    <TableCell>{new Date(order.created_at).toLocaleDateString()}</TableCell>
                    <TableCell className="font-mono text-xs">{order.unique_ref_no}</TableCell>
                    <TableCell>{order.investor_name}</TableCell>
                    <TableCell className="max-w-[200px] truncate" title={order.scheme_name}>{order.scheme_name}</TableCell>
                    <TableCell>{order.transaction_type_display}</TableCell>
                    <TableCell className="text-right">
                        {order.amount > 0 ? `₹${order.amount}` : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                        {order.units > 0 ? order.units : '-'}
                    </TableCell>
                    <TableCell>
                    <Badge className={getStatusColor(order.status)}>
                        {order.status_display}
                    </Badge>
                    </TableCell>
                    <TableCell className="max-w-[150px] truncate text-xs" title={order.bse_remarks}>
                        {order.bse_remarks || '-'}
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

export default OrderList;
