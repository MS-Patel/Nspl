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
import { Search, Plus, Loader2, ChevronLeft, ChevronRight, Edit, Trash2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Distributor } from '@/types/users';
import { useDebounce } from '@/hooks/use-debounce';
import { BulkUploadDialog } from '@/components/users/BulkUploadDialog';
import { useToast } from '@/components/ui/use-toast';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface PaginatedResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: Distributor[];
}

const DistributorList = () => {
  const [distributors, setDistributors] = useState<Distributor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const { toast } = useToast();
  const navigate = useNavigate();

  const debouncedSearch = useDebounce(search, 500);

  const fetchDistributors = async () => {
    setLoading(true);
    try {
      const queryParams = new URLSearchParams();
      queryParams.append('page', page.toString());
      if (debouncedSearch) {
          queryParams.append('search', debouncedSearch);
      }

      const result = await api.get<PaginatedResponse>(`/api/distributors/?${queryParams.toString()}`);

      if (result && result.results) {
          setDistributors(result.results);
          setTotalCount(result.count);
          setTotalPages(Math.ceil(result.count / 10));
      } else {
          setDistributors([]);
          setTotalCount(0);
      }
    } catch (error) {
      console.error('Error fetching Distributors:', error);
      toast({
          title: "Error",
          description: "Failed to fetch Distributors.",
          variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  useEffect(() => {
    fetchDistributors();
  }, [page, debouncedSearch]);

  const handleDelete = async (id: number) => {
      try {
          await api.delete(`/api/distributors/${id}/`);
          toast({
              title: "Success",
              description: "Distributor deleted successfully.",
          });
          fetchDistributors();
      } catch (error) {
          console.error("Delete failed", error);
          toast({
              title: "Error",
              description: "Failed to delete Distributor.",
              variant: "destructive",
          });
      }
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
            <h1 className="text-3xl font-bold tracking-tight">Distributors</h1>
            <p className="text-muted-foreground">Manage your distributor network.</p>
        </div>
        <div className="flex gap-2">
            <BulkUploadDialog
                triggerText="Import Distributors"
                title="Import Distributors"
                description="Upload a CSV or Excel file to bulk create Distributors. The file should contain ARN, name, email, etc."
                uploadUrl="/api/distributors/upload/"
                sampleUrl="/api/distributors/upload/sample/"
                onSuccess={fetchDistributors}
            />
            <Link to="/dashboard/distributors/new">
                <Button>
                    <Plus className="mr-2 h-4 w-4" /> Add New Distributor
                </Button>
            </Link>
        </div>
      </div>

      <Card>
        <CardHeader>
            <div className="flex items-center justify-between">
                <CardTitle>All Distributors ({totalCount})</CardTitle>
                <div className="relative w-64">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search by name, ARN..."
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
                        <TableHead>ARN</TableHead>
                        <TableHead>Code</TableHead>
                        <TableHead>RM</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                    </TableHeader>
                    <TableBody>
                    {distributors.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                No distributors found.
                            </TableCell>
                        </TableRow>
                    ) : (
                        distributors.map((d) => (
                        <TableRow key={d.id}>
                            <TableCell className="font-medium">
                                {d.name}
                                <div className="text-xs text-muted-foreground">{d.username}</div>
                            </TableCell>
                            <TableCell>{d.arn_number}</TableCell>
                            <TableCell>{d.broker_code}</TableCell>
                            <TableCell>{d.rm_name || '-'}</TableCell>
                            <TableCell>
                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                    d.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                }`}>
                                    {d.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </TableCell>
                            <TableCell className="text-right">
                                <div className="flex justify-end gap-2">
                                    <Button variant="ghost" size="icon" onClick={() => navigate(`/dashboard/distributors/${d.id}`)}>
                                        <Edit className="h-4 w-4" />
                                    </Button>

                                    <AlertDialog>
                                        <AlertDialogTrigger asChild>
                                            <Button variant="ghost" size="icon" className="text-red-500">
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </AlertDialogTrigger>
                                        <AlertDialogContent>
                                            <AlertDialogHeader>
                                                <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                                                <AlertDialogDescription>
                                                    This action cannot be undone. This will permanently delete the Distributor profile for <b>{d.name}</b>.
                                                </AlertDialogDescription>
                                            </AlertDialogHeader>
                                            <AlertDialogFooter>
                                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                                <AlertDialogAction onClick={() => handleDelete(d.id)} className="bg-red-600 hover:bg-red-700">
                                                    Delete
                                                </AlertDialogAction>
                                            </AlertDialogFooter>
                                        </AlertDialogContent>
                                    </AlertDialog>
                                </div>
                            </TableCell>
                        </TableRow>
                        ))
                    )}
                    </TableBody>
                </Table>

                <div className="flex items-center justify-end space-x-2 py-4">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
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
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
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

export default DistributorList;
