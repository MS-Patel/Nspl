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
import { TrendingUp, TrendingDown, IndianRupee, PieChart } from 'lucide-react';

interface Holding {
  id: number;
  scheme_name: string;
  folio: string;
  units: number;
  average_cost: number;
  current_nav: number;
  current_value: number;
  invested_value: number;
  gain_loss: number;
  gain_loss_percent: number;
  nav_date: string | null;
}

interface ValuationData {
  total_current_value: number;
  total_invested_value: number;
  total_gain_loss: number;
  holdings: Holding[];
}

interface InvestorDashboardData {
  valuation: ValuationData;
}

const InvestorDashboard = () => {
  const [data, setData] = useState<InvestorDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await api.get('/api/dashboard/investor/');
        setData(result);
      } catch (error) {
        console.error('Error fetching investor dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="p-8">Loading dashboard...</div>;
  }

  if (!data || !data.valuation) {
    // Handle empty state where valuation might be missing if no investor profile
    return (
        <div className="flex flex-col items-center justify-center h-[50vh] gap-4">
            <h2 className="text-xl font-semibold">Welcome to your dashboard</h2>
            <p className="text-muted-foreground">It looks like your investment profile is still being set up.</p>
        </div>
    );
  }

  const { total_current_value, total_invested_value, total_gain_loss, holdings } = data.valuation;
  const gainLossPercent = total_invested_value > 0 ? (total_gain_loss / total_invested_value) * 100 : 0;

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
        <p className="text-muted-foreground">Your investment overview.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Value</CardTitle>
            <IndianRupee className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(total_current_value)}</div>
            <p className="text-xs text-muted-foreground">Latest Portfolio Value</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Invested Value</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(total_invested_value)}</div>
            <p className="text-xs text-muted-foreground">Total Capital Invested</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Gain/Loss</CardTitle>
            {total_gain_loss >= 0 ? (
                <TrendingUp className="h-4 w-4 text-green-500" />
            ) : (
                <TrendingDown className="h-4 w-4 text-red-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${total_gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {total_gain_loss >= 0 ? '+' : ''}{formatCurrency(total_gain_loss)}
            </div>
            <p className={`text-xs ${total_gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {total_gain_loss >= 0 ? '+' : ''}{gainLossPercent.toFixed(2)}%
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Holdings</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Scheme</TableHead>
                <TableHead>Folio</TableHead>
                <TableHead className="text-right">Units</TableHead>
                <TableHead className="text-right">Avg Cost</TableHead>
                <TableHead className="text-right">NAV</TableHead>
                <TableHead className="text-right">Current Value</TableHead>
                <TableHead className="text-right">Gain/Loss</TableHead>
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
                    <TableCell className="font-medium max-w-[250px] truncate" title={holding.scheme_name}>
                        {holding.scheme_name}
                    </TableCell>
                    <TableCell>{holding.folio}</TableCell>
                    <TableCell className="text-right">{holding.units}</TableCell>
                    <TableCell className="text-right">{formatCurrency(holding.average_cost)}</TableCell>
                    <TableCell className="text-right">
                        <div>{holding.current_nav}</div>
                        <div className="text-[10px] text-muted-foreground">{holding.nav_date}</div>
                    </TableCell>
                    <TableCell className="text-right font-bold">{formatCurrency(holding.current_value)}</TableCell>
                    <TableCell className={`text-right ${holding.gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {holding.gain_loss >= 0 ? '+' : ''}{formatCurrency(holding.gain_loss)}
                        <br/>
                        <span className="text-xs">({holding.gain_loss_percent}%)</span>
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

export default InvestorDashboard;
