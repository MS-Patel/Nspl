import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Pencil } from "lucide-react";

interface AMC {
    id: number;
    name: string;
    code: string;
    is_active: boolean;
}

const AMCList = () => {
    const [amcs, setAmcs] = useState<AMC[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");

    // Edit Dialog State
    const [isEditOpen, setIsEditOpen] = useState(false);
    const [editingAMC, setEditingAMC] = useState<AMC | null>(null);
    const [editName, setEditName] = useState("");

    const fetchAMCs = async () => {
        setLoading(true);
        try {
            const params: any = {};
            if (search) params.search = search;
            const data: any = await api.get("/api/amc/", { params });
            // DRF ListCreateAPIView usually returns array or paginated object depending on settings.
            // If using standard pagination it returns { count: ..., results: [...] }
            // If simple list, array.
            // Let's assume pagination is off for AMC list or we handle both.
            if (Array.isArray(data)) {
                setAmcs(data);
            } else if (data.results) {
                setAmcs(data.results);
            }
        } catch (error) {
            console.error("Failed to fetch AMCs", error);
            toast.error("Failed to load AMCs");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAMCs();
    }, [search]); // Re-fetch on search change with debounce ideally, but simple for now

    const handleToggleStatus = async (amc: AMC) => {
        const newStatus = !amc.is_active;
        // Optimistic update
        setAmcs(amcs.map(a => a.id === amc.id ? { ...a, is_active: newStatus } : a));

        try {
            await api.patch(`/api/amc/${amc.id}/`, { is_active: newStatus });
            toast.success(`AMC ${amc.name} is now ${newStatus ? 'Active' : 'Inactive'}`);
        } catch (error) {
            // Revert on error
            setAmcs(amcs.map(a => a.id === amc.id ? { ...a, is_active: !newStatus } : a));
            toast.error("Failed to update status");
        }
    };

    const openEditDialog = (amc: AMC) => {
        setEditingAMC(amc);
        setEditName(amc.name);
        setIsEditOpen(true);
    };

    const handleSaveName = async () => {
        if (!editingAMC) return;
        try {
            await api.patch(`/api/amc/${editingAMC.id}/`, { name: editName });
            setAmcs(amcs.map(a => a.id === editingAMC.id ? { ...a, name: editName } : a));
            setIsEditOpen(false);
            toast.success("AMC name updated successfully");
        } catch (error) {
            toast.error("Failed to update name");
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-3xl font-bold tracking-tight">AMC Master</h2>
                <div className="flex items-center space-x-2">
                    <Input
                        placeholder="Search AMC..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-[300px]"
                    />
                </div>
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[100px]">ID</TableHead>
                            <TableHead>Code</TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {loading ? (
                            <TableRow>
                                <TableCell colSpan={5} className="text-center py-10">Loading...</TableCell>
                            </TableRow>
                        ) : amcs.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5} className="text-center py-10">No AMCs found.</TableCell>
                            </TableRow>
                        ) : (
                            amcs.map((amc) => (
                                <TableRow key={amc.id}>
                                    <TableCell className="font-medium">{amc.id}</TableCell>
                                    <TableCell>{amc.code}</TableCell>
                                    <TableCell>{amc.name}</TableCell>
                                    <TableCell>
                                        <div className="flex items-center space-x-2">
                                            <Switch
                                                checked={amc.is_active}
                                                onCheckedChange={() => handleToggleStatus(amc)}
                                            />
                                            <span className="text-sm text-muted-foreground">
                                                {amc.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <Button variant="ghost" size="sm" onClick={() => openEditDialog(amc)}>
                                            <Pencil className="h-4 w-4 mr-2" />
                                            Edit
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>Edit AMC Name</DialogTitle>
                        <DialogDescription>
                            Make changes to the AMC name here. Click save when you're done.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="name" className="text-right">
                                Name
                            </Label>
                            <Input
                                id="name"
                                value={editName}
                                onChange={(e) => setEditName(e.target.value)}
                                className="col-span-3"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button type="submit" onClick={handleSaveName}>Save changes</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
};

export default AMCList;
