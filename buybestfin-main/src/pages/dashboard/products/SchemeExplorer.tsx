import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";
import { Filter, X } from "lucide-react";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger, SheetFooter, SheetClose } from "@/components/ui/sheet";
import { Label } from "@/components/ui/label";

interface Scheme {
    id: number;
    name: string;
    scheme_code: string;
    isin: string;
    amc: number;
    amc_name: string;
    category: number;
    category_name: string;
    scheme_type: string;
    scheme_plan: string;
    min_purchase_amount: string;
    purchase_allowed: boolean;
    riskometer: string;
}

interface FilterOption {
    id: number;
    name: string;
}

const SchemeExplorer = () => {
    // Data State
    const [schemes, setSchemes] = useState<Scheme[]>([]);
    const [loading, setLoading] = useState(true);
    const [totalCount, setTotalCount] = useState(0);

    // Pagination State
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [nextPage, setNextPage] = useState<string | null>(null);
    const [prevPage, setPrevPage] = useState<string | null>(null);

    // Filter State
    const [search, setSearch] = useState("");
    const [selectedAmc, setSelectedAmc] = useState<string>("");
    const [selectedCategory, setSelectedCategory] = useState<string>("");
    const [selectedType, setSelectedType] = useState<string>("");
    const [selectedRisk, setSelectedRisk] = useState<string>("");

    // Filter Options
    const [amcOptions, setAmcOptions] = useState<FilterOption[]>([]);
    const [categoryOptions, setCategoryOptions] = useState<FilterOption[]>([]);
    const schemeTypes = ["Open Ended", "Close Ended", "Interval Fund"];
    const riskOptions = ["Low", "Low to Moderate", "Moderate", "Moderately High", "High", "Very High"];

    useEffect(() => {
        const fetchOptions = async () => {
            try {
                const [amcRes, catRes] = await Promise.all([
                    api.get("/api/amc/"),
                    api.get("/api/categories/")
                ]);
                // Handle different response structures if needed
                if (Array.isArray(amcRes)) setAmcOptions(amcRes);
                else if (amcRes.results) setAmcOptions(amcRes.results);

                if (Array.isArray(catRes)) setCategoryOptions(catRes);
                else if (catRes.results) setCategoryOptions(catRes.results);

            } catch (e) {
                console.error("Failed to load filter options", e);
            }
        };
        fetchOptions();
    }, []);

    const fetchSchemes = async () => {
        setLoading(true);
        try {
            const params: any = {
                page: page,
                page_size: pageSize,
                ordering: 'name',
            };
            if (search) params.search = search;
            if (selectedAmc && selectedAmc !== "all") params.amc = selectedAmc;
            if (selectedCategory && selectedCategory !== "all") params.category = selectedCategory;
            if (selectedType && selectedType !== "all") params.scheme_type = selectedType;
            if (selectedRisk && selectedRisk !== "all") params.riskometer = selectedRisk;

            const data: any = await api.get("/api/schemes/", { params });

            if (data.results) {
                setSchemes(data.results);
                setTotalCount(data.count);
                setNextPage(data.next);
                setPrevPage(data.previous);
            } else {
                setSchemes([]);
            }
        } catch (error) {
            console.error("Failed to fetch schemes", error);
            setSchemes([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSchemes();
    }, [page, pageSize, selectedAmc, selectedCategory, selectedType, selectedRisk]); // Search is manual or debounced? Let's keep it manual trigger for now or effect if we debounce

    // Handle Search on Enter or Button
    const handleSearch = () => {
        setPage(1);
        fetchSchemes();
    };

    const clearFilters = () => {
        setSearch("");
        setSelectedAmc("");
        setSelectedCategory("");
        setSelectedType("");
        setSelectedRisk("");
        setPage(1);
    };

    const totalPages = Math.ceil(totalCount / pageSize);

    return (
        <div className="space-y-6">
             <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <h2 className="text-3xl font-bold tracking-tight">Scheme Explorer</h2>
                <div className="flex items-center gap-2 w-full sm:w-auto">
                     <Input
                        placeholder="Search by Name, ISIN, Code..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        className="w-full sm:w-[300px]"
                    />
                    <Button onClick={handleSearch}>Search</Button>
                    <Sheet>
                        <SheetTrigger asChild>
                             <Button variant="outline" size="icon">
                                <Filter className="h-4 w-4" />
                             </Button>
                        </SheetTrigger>
                        <SheetContent>
                            <SheetHeader>
                                <SheetTitle>Filter Schemes</SheetTitle>
                                <SheetDescription>
                                    Apply filters to narrow down the scheme list.
                                </SheetDescription>
                            </SheetHeader>
                            <div className="grid gap-4 py-4">
                                <div className="space-y-2">
                                    <Label>AMC</Label>
                                    <Select value={selectedAmc} onValueChange={setSelectedAmc}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select AMC" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="all">All AMCs</SelectItem>
                                            {amcOptions.map(amc => (
                                                <SelectItem key={amc.id} value={amc.id.toString()}>{amc.name}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Category</Label>
                                    <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select Category" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="all">All Categories</SelectItem>
                                            {categoryOptions.map(c => (
                                                <SelectItem key={c.id} value={c.id.toString()}>{c.name}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label>Type</Label>
                                    <Select value={selectedType} onValueChange={setSelectedType}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select Type" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="all">All Types</SelectItem>
                                            {schemeTypes.map(t => (
                                                <SelectItem key={t} value={t}>{t}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                 <div className="space-y-2">
                                    <Label>Riskometer</Label>
                                    <Select value={selectedRisk} onValueChange={setSelectedRisk}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select Risk" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="all">All Risks</SelectItem>
                                            {riskOptions.map(r => (
                                                <SelectItem key={r} value={r}>{r}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <Button variant="secondary" onClick={clearFilters} className="mt-4">
                                    <X className="mr-2 h-4 w-4" /> Clear Filters
                                </Button>
                            </div>
                             <SheetFooter>
                                <SheetClose asChild>
                                    <Button onClick={() => setPage(1)}>Apply Filters</Button>
                                </SheetClose>
                            </SheetFooter>
                        </SheetContent>
                    </Sheet>
                </div>
            </div>

             <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[80px]">ID</TableHead>
                            <TableHead>Scheme Name</TableHead>
                            <TableHead>AMC</TableHead>
                            <TableHead>Category</TableHead>
                            <TableHead>Plan</TableHead>
                            <TableHead>Min Inv</TableHead>
                            <TableHead>Risk</TableHead>
                            <TableHead className="text-right">Active</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {loading ? (
                             <TableRow>
                                <TableCell colSpan={8} className="text-center py-10">Loading...</TableCell>
                            </TableRow>
                        ) : schemes.length === 0 ? (
                             <TableRow>
                                <TableCell colSpan={8} className="text-center py-10">No schemes found.</TableCell>
                            </TableRow>
                        ) : (
                            schemes.map((s) => (
                                <TableRow key={s.id}>
                                    <TableCell className="text-xs text-muted-foreground">{s.id}</TableCell>
                                    <TableCell className="font-medium">
                                        <div>{s.name}</div>
                                        <div className="text-xs text-muted-foreground">ISIN: {s.isin} | Code: {s.scheme_code}</div>
                                    </TableCell>
                                    <TableCell>{s.amc_name}</TableCell>
                                    <TableCell>{s.category_name}</TableCell>
                                    <TableCell><Badge variant="outline">{s.scheme_plan}</Badge></TableCell>
                                    <TableCell>₹{s.min_purchase_amount}</TableCell>
                                    <TableCell>{s.riskometer}</TableCell>
                                    <TableCell className="text-right">
                                        <span className={s.purchase_allowed ? "text-green-600" : "text-red-600"}>
                                            {s.purchase_allowed ? "Yes" : "No"}
                                        </span>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                    Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of {totalCount} entries
                </div>
                <div className="flex items-center space-x-2">
                    <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={!prevPage}>Previous</Button>
                     <div className="text-sm font-medium">Page {page} of {totalPages || 1}</div>
                    <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={!nextPage}>Next</Button>
                </div>
            </div>
        </div>
    );
};

export default SchemeExplorer;
