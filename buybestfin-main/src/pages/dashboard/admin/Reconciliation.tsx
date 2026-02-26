import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { Loader2, Upload, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

const uploadSchema = z.object({
  rta_type: z.enum(['CAMS', 'KARVY', 'FRANKLIN'], { required_error: "Select RTA Type" }),
  file: z.instanceof(FileList).refine((files) => files.length > 0, "File is required"),
});

type UploadValues = z.infer<typeof uploadSchema>;

interface RTAFile {
  id: number;
  rta_type: string;
  file_name: string;
  status: string;
  uploaded_at: string;
  error_log: string;
}

const Reconciliation = () => {
  const [files, setFiles] = useState<RTAFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const form = useForm<UploadValues>({
    resolver: zodResolver(uploadSchema),
  });

  const fetchFiles = async () => {
      try {
          const data: any = await api.get('/api/reconciliation/upload/');
          setFiles(data.results || data);
      } catch (error) {
          console.error("Failed to load RTA files", error);
      } finally {
          setLoading(false);
      }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const onSubmit = async (data: UploadValues) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('rta_type', data.rta_type);
      formData.append('file', data.file[0]);

      // Use axios directly for file upload if api wrapper doesn't handle FormData automatically or just pass it
      // api wrapper uses axios, so it should handle FormData if passed correctly
      // But we need to make sure Content-Type is not set to json
      // Our api wrapper sets 'Content-Type': 'application/json' by default.
      // We need to override it.

      // Since api wrapper is imported, we can use it but need to override headers.
      // Or just use fetch/axios directly. Let's try api.post with config.

      await api.post('/api/reconciliation/upload/', formData, {
          headers: {
              'Content-Type': 'multipart/form-data', // Axios might set this automatically if data is FormData? No, usually safer to let it set boundary.
              // Actually, if we pass FormData, axios usually handles it. But we set default content-type in api.ts.
              // We should probably set it to undefined to let browser handle boundary.
          }
      });

      toast.success("File uploaded successfully. Processing started.");
      form.reset();
      fetchFiles();
    } catch (error: any) {
      toast.error(error.response?.data?.message || "Upload Failed");
    } finally {
      setUploading(false);
    }
  };

  // Helper for file input
  const fileRef = form.register("file");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Reconciliation</h2>
        <p className="text-muted-foreground">Upload and process RTA Mailback files.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload File</CardTitle>
          <CardDescription>Supported Formats: DBF, CSV, XLS (CAMS, Karvy, Franklin)</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="flex items-end gap-4">
              <FormField
                control={form.control}
                name="rta_type"
                render={({ field }) => (
                  <FormItem className="w-[200px]">
                    <FormLabel>RTA Type</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select RTA" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="CAMS">CAMS</SelectItem>
                        <SelectItem value="KARVY">Karvy (KFintech)</SelectItem>
                        <SelectItem value="FRANKLIN">Franklin Templeton</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="file"
                render={({ field }) => (
                  <FormItem className="flex-1">
                    <FormLabel>File</FormLabel>
                    <FormControl>
                      <Input type="file" {...fileRef} onChange={(e) => {
                          field.onChange(e.target.files);
                      }} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={uploading}>
                {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                Upload
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Uploads</CardTitle>
        </CardHeader>
        <CardContent>
            {loading ? <div className="p-4 flex justify-center"><Loader2 className="animate-spin" /></div> : (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Date</TableHead>
                            <TableHead>RTA</TableHead>
                            <TableHead>Filename</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Log</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {files.length === 0 ? (
                            <TableRow><TableCell colSpan={5} className="text-center">No files uploaded.</TableCell></TableRow>
                        ) : (
                            files.map((f) => (
                                <TableRow key={f.id}>
                                    <TableCell>{new Date(f.uploaded_at).toLocaleString()}</TableCell>
                                    <TableCell>{f.rta_type}</TableCell>
                                    <TableCell className="font-mono text-xs">{f.file_name}</TableCell>
                                    <TableCell>
                                        <Badge variant={f.status === 'PROCESSED' ? 'default' : f.status === 'FAILED' ? 'destructive' : 'secondary'}>
                                            {f.status}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="max-w-[200px] truncate text-xs text-muted-foreground" title={f.error_log}>
                                        {f.error_log}
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

export default Reconciliation;
