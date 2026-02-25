import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Loader2, ArrowLeft, Edit2, Upload, RefreshCw, CheckCircle, XCircle, AlertTriangle, MoreVertical } from 'lucide-react';
import { Investor } from '@/types/investor';
import { useToast } from '@/hooks/use-toast';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const InvestorDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [investor, setInvestor] = useState<Investor | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Modal States
  const [isEditProfileOpen, setIsEditProfileOpen] = useState(false);
  const [editFormData, setEditFormData] = useState<any>({});

  useEffect(() => {
    fetchInvestor();
  }, [id]);

  const fetchInvestor = async () => {
    setLoading(true);
    try {
      const data = await api.get<Investor>(`/api/investors/${id}/`);
      setInvestor(data);
      setEditFormData(data); // Initialize edit form
    } catch (error) {
      console.error('Error fetching investor details:', error);
      toast({
        title: "Error",
        description: "Failed to load investor details.",
        variant: "destructive"
      });
    } finally {
        setLoading(false);
    }
  };

  const handleBSEAction = async (action: string, endpoint: string) => {
      setActionLoading(action);
      try {
          const response: any = await api.post(`/api/investors/${id}/${endpoint}/`);
          toast({
              title: "Success",
              description: response.message || "Action completed successfully.",
          });
          fetchInvestor(); // Refresh data
      } catch (error: any) {
          console.error(`${action} error:`, error);
          toast({
              title: "Error",
              description: error.response?.data?.message || "Action failed.",
              variant: "destructive"
          });
      } finally {
          setActionLoading(null);
      }
  };

  const handleUpdateProfile = async () => {
      try {
          await api.patch(`/api/investors/${id}/`, editFormData);
          toast({ title: "Success", description: "Profile updated successfully." });
          setIsEditProfileOpen(false);
          fetchInvestor();
      } catch (error: any) {
          toast({
              title: "Error",
              description: "Failed to update profile.",
              variant: "destructive"
          });
      }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!investor) {
    return <div>Investor not found.</div>;
  }

  return (
    <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
                <Link to="/dashboard/investors">
                    <Button variant="outline" size="icon">
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                </Link>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{investor.name}</h1>
                    <div className="flex items-center gap-2 text-muted-foreground mt-1">
                        <span>PAN: {investor.pan}</span>
                        <span>•</span>
                        <span>{investor.email}</span>
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline">
                            Actions <MoreVertical className="ml-2 h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuLabel>BSE Integration</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => handleBSEAction('push', 'push-bse')}>
                            {actionLoading === 'push' && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
                            Push to BSE
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleBSEAction('auth', 'trigger-auth')}>
                             {actionLoading === 'auth' && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
                            Trigger Auth (Email/SMS)
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleBSEAction('fatca', 'fatca-upload')}>
                             {actionLoading === 'fatca' && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
                            Upload FATCA
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleBSEAction('kyc', 'toggle-kyc')}>
                            Toggle KYC Status
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>

                <Dialog open={isEditProfileOpen} onOpenChange={setIsEditProfileOpen}>
                    <DialogTrigger asChild>
                        <Button>Edit Profile</Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px]">
                        <DialogHeader>
                            <DialogTitle>Edit Profile</DialogTitle>
                            <DialogDescription>
                                Update basic profile information.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="name" className="text-right">Name</Label>
                                <Input id="name" value={editFormData.name} disabled className="col-span-3 bg-muted" />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="mobile" className="text-right">Mobile</Label>
                                <Input
                                    id="mobile"
                                    value={editFormData.mobile}
                                    onChange={(e) => setEditFormData({...editFormData, mobile: e.target.value})}
                                    className="col-span-3"
                                />
                            </div>
                             <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="email" className="text-right">Email</Label>
                                <Input
                                    id="email"
                                    value={editFormData.email}
                                    onChange={(e) => setEditFormData({...editFormData, email: e.target.value})}
                                    className="col-span-3"
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button onClick={handleUpdateProfile}>Save changes</Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>
        </div>

        {/* Quick Stats / Status Cards */}
        <div className="grid gap-4 md:grid-cols-4">
            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">BSE Status</CardTitle>
                    {investor.ucc_code ? <CheckCircle className="h-4 w-4 text-green-500"/> : <AlertTriangle className="h-4 w-4 text-yellow-500"/>}
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{investor.ucc_code ? 'Registered' : 'Not Registered'}</div>
                    <p className="text-xs text-muted-foreground">{investor.ucc_code || 'Push to BSE to generate UCC'}</p>
                </CardContent>
            </Card>
            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Nominee Auth</CardTitle>
                    <RefreshCw className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{investor.nominee_auth_status_display}</div>
                    <p className="text-xs text-muted-foreground">Last verified: {investor.last_verified_at ? new Date(investor.last_verified_at).toLocaleDateString() : 'Never'}</p>
                </CardContent>
            </Card>
             <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">KYC Status</CardTitle>
                    {investor.kyc_status ? <CheckCircle className="h-4 w-4 text-green-500"/> : <XCircle className="h-4 w-4 text-red-500"/>}
                </CardHeader>
                <CardContent>
                    <div className="text-2xl font-bold">{investor.kyc_status ? 'Verified' : 'Pending'}</div>
                    <p className="text-xs text-muted-foreground">Type: {investor.kyc_type_display}</p>
                </CardContent>
            </Card>
        </div>

        {/* Tabs for Details */}
        <Tabs defaultValue="overview" className="w-full">
            <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="bank">Bank Accounts</TabsTrigger>
                <TabsTrigger value="nominees">Nominees</TabsTrigger>
                <TabsTrigger value="documents">Documents</TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
                <Card>
                    <CardHeader>
                        <CardTitle>Personal Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <p className="font-medium text-muted-foreground">Date of Birth</p>
                                <p>{investor.dob}</p>
                            </div>
                            <div>
                                <p className="font-medium text-muted-foreground">Tax Status</p>
                                <p>{investor.tax_status_display}</p>
                            </div>
                            <div>
                                <p className="font-medium text-muted-foreground">Occupation</p>
                                <p>{investor.occupation_display}</p>
                            </div>
                            <div>
                                <p className="font-medium text-muted-foreground">Holding Nature</p>
                                <p>{investor.holding_nature_display}</p>
                            </div>
                            <div>
                                <p className="font-medium text-muted-foreground">Address</p>
                                <p>{investor.address_1} {investor.address_2}</p>
                                <p>{investor.city}, {investor.state} - {investor.pincode}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </TabsContent>

            <TabsContent value="bank">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle>Bank Accounts</CardTitle>
                        <Button size="sm" variant="outline"><Upload className="h-4 w-4 mr-2"/> Add Bank</Button>
                    </CardHeader>
                    <CardContent>
                        {investor.bank_accounts && investor.bank_accounts.length > 0 ? (
                            <div className="space-y-4">
                                {investor.bank_accounts.map((bank: any) => (
                                    <div key={bank.id} className="flex justify-between items-center p-4 border rounded-lg">
                                        <div>
                                            <p className="font-bold">{bank.bank_name} {bank.is_default && <Badge variant="secondary">Default</Badge>}</p>
                                            <p className="text-sm text-muted-foreground">{bank.account_number} • {bank.ifsc_code}</p>
                                            <p className="text-xs text-muted-foreground">{bank.account_type_display}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-muted-foreground">No bank accounts linked.</p>
                        )}
                    </CardContent>
                </Card>
            </TabsContent>

            <TabsContent value="nominees">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle>Nominees</CardTitle>
                        <Button size="sm" variant="outline"><Upload className="h-4 w-4 mr-2"/> Add Nominee</Button>
                    </CardHeader>
                    <CardContent>
                         {investor.nominees && investor.nominees.length > 0 ? (
                            <div className="space-y-4">
                                {investor.nominees.map((nom: any) => (
                                    <div key={nom.id} className="flex justify-between items-center p-4 border rounded-lg">
                                        <div>
                                            <p className="font-bold">{nom.name} <Badge variant="outline">{nom.percentage}%</Badge></p>
                                            <p className="text-sm text-muted-foreground">{nom.relationship_display}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-muted-foreground">No nominees added.</p>
                        )}
                    </CardContent>
                </Card>
            </TabsContent>

            <TabsContent value="documents">
                <Card>
                    <CardHeader>
                        <CardTitle>Documents</CardTitle>
                        <CardDescription>KYC and other related documents.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <p className="text-muted-foreground">No documents uploaded.</p>
                    </CardContent>
                </Card>
            </TabsContent>
        </Tabs>
    </div>
  );
};

export default InvestorDetail;
