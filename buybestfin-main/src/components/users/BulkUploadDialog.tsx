import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface BulkUploadDialogProps {
  triggerText: string;
  title: string;
  description: string;
  uploadUrl: string;
  sampleUrl: string;
  onSuccess: () => void;
}

export function BulkUploadDialog({
  triggerText,
  title,
  description,
  uploadUrl,
  sampleUrl,
  onSuccess,
}: BulkUploadDialogProps) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      // Pass undefined as Content-Type to let browser set it with boundary
      const response: any = await api.post(uploadUrl, formData, {
        headers: {
            "Content-Type": undefined,
        },
      });

      if (response.status === 'success') {
          toast({
            title: "Upload Successful",
            description: response.message,
          });
          setOpen(false);
          setFile(null);
          onSuccess();
      } else if (response.status === 'warning') {
          toast({
              title: "Upload Completed with Warnings",
              description: response.message,
              variant: "destructive",
          });
          setOpen(false);
          setFile(null);
          onSuccess();
      } else {
          // If status is error but not thrown
          throw new Error(response.message || "Upload failed");
      }

    } catch (error: any) {
      console.error("Upload error:", error);
      toast({
        title: "Upload Failed",
        description: error.response?.data?.message || error.message || "An error occurred during upload.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Upload className="mr-2 h-4 w-4" />
          {triggerText}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid w-full max-w-sm items-center gap-1.5">
            <Label htmlFor="file">Select File (CSV/Excel)</Label>
            <Input
                id="file"
                type="file"
                accept=".csv, .xlsx, .xls"
                onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
            />
          </div>
          <div className="flex justify-start">
              <Button variant="link" className="p-0 h-auto text-sm text-primary" asChild>
                  <a href={sampleUrl} download>Download Sample Template</a>
              </Button>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleUpload} disabled={!file || loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Upload
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
