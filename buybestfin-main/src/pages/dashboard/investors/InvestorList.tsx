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
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Plus, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Investor } from '@/types/investor';

const InvestorList = () => {
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await api.get<Investor[]>('/api/investors/');
        // Check if result is wrapped in { results: ... } if using pagination, but ListAPIView returns array if pagination is off
        // Or { count, next, previous, results } if pagination is on.
        // Assuming pagination is default ON in DRF, result will be { results: [] }
        // Let's assume pagination is OFF for now or handle both.
        if (Array.isArray(result)) {
            setInvestors(result);
        } else if (result && Array.isArray((result as any).results)) {
            setInvestors((result as any).results);
        } else {
            console.error('Unexpected API response format:', result);
            setInvestors([]);
        }
      } catch (error) {
        console.error('Error fetching investors:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const filteredInvestors = investors.filter((inv) =>
    (inv.name || '').toLowerCase().includes(search.toLowerCase()) ||
    (inv.pan || '').toLowerCase().includes(search.toLowerCase()) ||
    (inv.email || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
            <h1 className="text-3xl font-bold tracking-tight">Investors</h1>
            <p className="text-muted-foreground">Manage your investor base.</p>
        </div>
        <Button disabled>
            <Plus className="mr-2 h-4 w-4" /> Onboard Investor (Coming Soon)
        </Button>
      </div>

      <Card>
        <CardHeader>
            <div className="flex items-center justify-between">
                <CardTitle>All Investors</CardTitle>
                <div className="relative w-64">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search investors..."
                        className="pl-8"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
            </div>
        </CardHeader>
        <CardContent>
            {loading ? (
                <div className="flex justify-center p-8">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : (
                <Table>
                    <TableHeader>
                    <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>PAN</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                    </TableHeader>
                    <TableBody>
                    {filteredInvestors.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                                No investors found.
                            </TableCell>
                        </TableRow>
                    ) : (
                        filteredInvestors.map((inv) => (
                        <TableRow key={inv.id}>
                            <TableCell className="font-medium">
                                <Link to={`/dashboard/investors/${inv.id}`} className="hover:underline text-primary">
                                    {inv.name}
                                </Link>
                                <div className="text-xs text-muted-foreground">{inv.username}</div>
                            </TableCell>
                            <TableCell>{inv.pan}</TableCell>
                            <TableCell>{inv.email}</TableCell>
                            <TableCell>
                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                    inv.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                }`}>
                                    {inv.status}
                                </span>
                            </TableCell>
                            <TableCell className="text-right">
                                <Link to={`/dashboard/investors/${inv.id}`}>
                                    <Button variant="ghost" size="sm">View</Button>
                                </Link>
                            </TableCell>
                        </TableRow>
                        ))
                    )}
                    </TableBody>
                </Table>
            )}
        </CardContent>
      </Card>
    </div>
  );
};

export default InvestorList;
