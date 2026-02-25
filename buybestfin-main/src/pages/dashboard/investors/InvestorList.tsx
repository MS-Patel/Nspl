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
import { Search, Plus, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Investor } from '@/types/investor';
import { useDebounce } from '@/hooks/use-debounce';

interface PaginatedResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: Investor[];
}

const InvestorList = () => {
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const debouncedSearch = useDebounce(search, 500);

  useEffect(() => {
    // Reset to page 1 when search changes
    setPage(1);
  }, [debouncedSearch]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const queryParams = new URLSearchParams();
        queryParams.append('page', page.toString());
        if (debouncedSearch) {
            queryParams.append('search', debouncedSearch);
        }

        const result = await api.get<PaginatedResponse | Investor[]>(`/api/investors/?${queryParams.toString()}`);

        if ('results' in result) {
            setInvestors(result.results);
            setTotalCount(result.count);
            setTotalPages(Math.ceil(result.count / 10)); // Assuming page size 10
        } else if (Array.isArray(result)) {
            // Fallback for non-paginated API
            setInvestors(result);
            setTotalCount(result.length);
            setTotalPages(1);
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
  }, [page, debouncedSearch]);

  const handleNextPage = () => {
    if (page < totalPages) setPage(page + 1);
  };

  const handlePrevPage = () => {
    if (page > 1) setPage(page - 1);
  };

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
                <CardTitle>All Investors ({totalCount})</CardTitle>
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
                <>
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
                    {investors.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                                No investors found.
                            </TableCell>
                        </TableRow>
                    ) : (
                        investors.map((inv) => (
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

                {/* Pagination Controls */}
                <div className="flex items-center justify-end space-x-2 py-4">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handlePrevPage}
                        disabled={page === 1}
                    >
                        <ChevronLeft className="h-4 w-4" />
                        Previous
                    </Button>
                    <div className="text-sm font-medium">
                        Page {page} of {totalPages}
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleNextPage}
                        disabled={page >= totalPages}
                    >
                        Next
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>
                </>
            )}
        </CardContent>
      </Card>
    </div>
  );
};

export default InvestorList;
