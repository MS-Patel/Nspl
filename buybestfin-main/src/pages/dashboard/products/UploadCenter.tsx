import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Upload, FileText, AlertCircle, CheckCircle } from "lucide-react";

const UploadCenter = () => {
    const [schemeFile, setSchemeFile] = useState<File | null>(null);
    const [navFile, setNavFile] = useState<File | null>(null);
    const [loadingScheme, setLoadingScheme] = useState(false);
    const [loadingNav, setLoadingNav] = useState(false);

    const handleSchemeUpload = async () => {
        if (!schemeFile) {
            toast.error("Please select a file first.");
            return;
        }

        setLoadingScheme(true);
        const formData = new FormData();
        formData.append("file", schemeFile);

        try {
            const response: any = await api.post("/api/schemes/upload/", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            });
            toast.success(response.message);
            if (response.errors && response.errors.length > 0) {
                 toast.warning(`Completed with errors: ${response.errors.length} issues found.`);
                 console.warn("Upload Errors:", response.errors);
            }
            setSchemeFile(null);
            // Reset input? controlled input is tricky with file, usually key reset or ref
        } catch (error: any) {
            console.error("Upload failed", error);
             toast.error(error.response?.data?.error || "Scheme upload failed.");
        } finally {
            setLoadingScheme(false);
        }
    };

    const handleNavUpload = async () => {
        if (!navFile) {
            toast.error("Please select a file first.");
            return;
        }

        setLoadingNav(true);
        const formData = new FormData();
        formData.append("file", navFile);

        try {
            const response: any = await api.post("/api/navs/upload/", formData, {
                 headers: {
                    "Content-Type": "multipart/form-data",
                },
            });
            toast.success(response.message);
             if (response.errors && response.errors.length > 0) {
                 toast.warning(`Completed with errors: ${response.errors.length} issues found.`);
            }
            setNavFile(null);
        } catch (error: any) {
             console.error("Upload failed", error);
             toast.error(error.response?.data?.error || "NAV upload failed.");
        } finally {
            setLoadingNav(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight">Upload Center</h2>
                <p className="text-muted-foreground">Manage bulk data imports for Products and NAVs.</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Scheme Master Import</CardTitle>
                        <CardDescription>Upload Scheme Master file (CSV/Excel) to update product catalog.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid w-full max-w-sm items-center gap-1.5">
                            <Label htmlFor="scheme-file">Scheme File</Label>
                            <Input
                                id="scheme-file"
                                type="file"
                                accept=".csv, .xlsx, .xls"
                                onChange={(e) => setSchemeFile(e.target.files ? e.target.files[0] : null)}
                            />
                        </div>
                        <div className="bg-muted p-4 rounded-md text-sm text-muted-foreground">
                            <p className="font-medium mb-1">Requirements:</p>
                            <ul className="list-disc pl-4 space-y-1">
                                <li>Headers: Scheme Code, Scheme Name, ISIN, AMC Code, etc.</li>
                                <li>Supported Formats: CSV, Excel (.xlsx)</li>
                            </ul>
                        </div>
                    </CardContent>
                    <CardFooter className="flex justify-between">
                        <Button variant="outline" asChild>
                             <a href="/schemes/upload/sample/">Download Sample</a>
                        </Button>
                        <Button onClick={handleSchemeUpload} disabled={loadingScheme || !schemeFile}>
                            {loadingScheme ? "Uploading..." : "Upload Schemes"}
                        </Button>
                    </CardFooter>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>NAV History Import</CardTitle>
                        <CardDescription>Upload historical NAV data for schemes.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid w-full max-w-sm items-center gap-1.5">
                            <Label htmlFor="nav-file">NAV File</Label>
                             <Input
                                id="nav-file"
                                type="file"
                                accept=".csv, .xlsx, .xls"
                                onChange={(e) => setNavFile(e.target.files ? e.target.files[0] : null)}
                            />
                        </div>
                         <div className="bg-muted p-4 rounded-md text-sm text-muted-foreground">
                            <p className="font-medium mb-1">Requirements:</p>
                            <ul className="list-disc pl-4 space-y-1">
                                <li>Headers: Scheme Code, Date, Net Asset Value</li>
                                <li>Date Format: DD-MM-YYYY or YYYY-MM-DD</li>
                            </ul>
                        </div>
                    </CardContent>
                    <CardFooter className="flex justify-between">
                         <Button variant="outline" asChild>
                             <a href="/navs/upload/sample/">Download Sample</a>
                        </Button>
                        <Button onClick={handleNavUpload} disabled={loadingNav || !navFile}>
                            {loadingNav ? "Uploading..." : "Upload NAVs"}
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
};

export default UploadCenter;
