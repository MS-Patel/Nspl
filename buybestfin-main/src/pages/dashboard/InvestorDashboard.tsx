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
import { TrendingUp, TrendingDown, IndianRupee, PieChart as PieChartIcon, Activity } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

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

interface AnalyticsData {
  total_value: number;
  asset_allocation: { name: string; value: number; percentage: number }[];
  sector_allocation: { name: string; value: number; percentage: number }[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

const InvestorDashboard = () => {
  const [valuation, setValuation] = useState<ValuationData | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [valRes, analyticsRes] = await Promise.all([
            api.get('/api/dashboard/investor/'),
            api.get('/api/portfolio/analytics/')
        ]);

        // Use type assertion or check if response has data property
        setValuation((valRes as any).valuation);
        setAnalytics(analyticsRes as any);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="p-8 flex items-center justify-center h-full"><Activity className="animate-spin mr-2"/> Loading dashboard...</div>;
  }

  if (!valuation) {
    return (
        <div className="flex flex-col items-center justify-center h-[50vh] gap-4">
            <h2 className="text-xl font-semibold">Welcome to your dashboard</h2>
            <p className="text-muted-foreground">It looks like your investment profile is still being set up.</p>
        </div>
    );
  }

  const { total_current_value, total_invested_value, total_gain_loss, holdings } = valuation;
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
        <h1 className="text-3xl font-bold tracking-tight">Portfolio Overview</h1>
        <p className="text-muted-foreground">Track your wealth and performance.</p>
      </div>

      {/* Summary Cards */}
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
            <PieChartIcon className="h-4 w-4 text-muted-foreground" />
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
                {total_gain_loss >= 0 ? '+' : ''}{gainLossPercent.toFixed(2)}% Returns
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Charts */}
      {analytics && (
          <div className="grid gap-4 md:grid-cols-2">
              <Card>
                  <CardHeader>
                      <CardTitle>Asset Allocation</CardTitle>
                      <CardDescription>Distribution by Asset Class</CardDescription>
                  </CardHeader>
                  <CardContent className="h-[300px]">
                      {analytics.asset_allocation.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={analytics.asset_allocation}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {analytics.asset_allocation.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <RechartsTooltip formatter={(value: number) => formatCurrency(value)} />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                      ) : (
                          <div className="flex items-center justify-center h-full text-muted-foreground">No data available</div>
                      )}
                  </CardContent>
              </Card>

              <Card>
                  <CardHeader>
                      <CardTitle>Sector Allocation</CardTitle>
                      <CardDescription>Top Sectors in your Portfolio</CardDescription>
                  </CardHeader>
                  <CardContent className="h-[300px]">
                      {analytics.sector_allocation.length > 0 ? (
                          <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={analytics.sector_allocation.slice(0, 5)} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                                  <XAxis type="number" hide />
                                  <YAxis dataKey="name" type="category" width={100} tick={{fontSize: 12}} />
                                  <RechartsTooltip formatter={(value: number) => formatCurrency(value)} />
                                  <Bar dataKey="value" fill="#82ca9d" radius={[0, 4, 4, 0]}>
                                    {analytics.sector_allocation.slice(0, 5).map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                  </Bar>
                              </BarChart>
                          </ResponsiveContainer>
                      ) : (
                          <div className="flex items-center justify-center h-full text-muted-foreground">No data available</div>
                      )}
                  </CardContent>
              </Card>
          </div>
      )}

      {/* Holdings Table */}
      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Top Holdings</CardTitle>
          <CardDescription>Your current investments.</CardDescription>
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
                holdings.slice(0, 5).map((holding) => (
                  <TableRow key={holding.id}>
                    <TableCell className="font-medium max-w-[200px] truncate" title={holding.scheme_name}>
                        {holding.scheme_name}
                    </TableCell>
                    <TableCell className="text-xs font-mono">{holding.folio}</TableCell>
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
