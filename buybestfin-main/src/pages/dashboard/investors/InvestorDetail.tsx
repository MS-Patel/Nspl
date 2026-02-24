import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, Loader2, Download, ExternalLink, RefreshCw } from 'lucide-react';
import { Investor } from '@/types/investor';
import { useToast } from "@/hooks/use-toast";

const InvestorDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [investor, setInvestor] = useState<Investor | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchInvestor = async () => {
    setLoading(true);
    try {
      const result = await api.get<Investor>(`/api/investors/${id}/`);
      setInvestor(result);
    } catch (error) {
      console.error('Error fetching investor details:', error);
      toast({
        title: "Error",
        description: "Failed to load investor details.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) fetchInvestor();
  }, [id]);

  if (loading) {
    return (
        <div className="flex flex-col items-center justify-center h-[50vh] gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading investor details...</p>
        </div>
    );
  }

  if (!investor) {
    return (
        <div className="flex flex-col items-center justify-center h-[50vh] gap-4">
            <p className="text-red-500">Investor not found.</p>
            <Link to="/dashboard/investors">
                <Button variant="outline"><ArrowLeft className="mr-2 h-4 w-4"/> Back to List</Button>
            </Link>
        </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
            <Link to="/dashboard/investors">
                <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
            </Link>
            <div>
                <h1 className="text-3xl font-bold tracking-tight">{investor.name}</h1>
                <div className="flex items-center gap-2 text-muted-foreground">
                    <span>{investor.username}</span>
                    <span>•</span>
                    <span>{investor.email}</span>
                </div>
            </div>
        </div>
        <div className="flex gap-2">
            <Button variant="outline" onClick={fetchInvestor}>
                <RefreshCw className="mr-2 h-4 w-4" /> Refresh
            </Button>
            {/* Add BSE Actions here later */}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Sidebar Info */}
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Status Overview</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex justify-between items-center">
                        <span className="text-sm font-medium">Account Status</span>
                        <Badge variant={investor.status === 'Active' ? 'default' : 'destructive'}>
                            {investor.status}
                        </Badge>
                    </div>
                    <Separator />
                    <div className="flex justify-between items-center">
                        <span className="text-sm font-medium">KYC Status</span>
                        <Badge variant={investor.kyc_status ? 'outline' : 'destructive'} className={investor.kyc_status ? 'text-green-600 border-green-600' : ''}>
                            {investor.kyc_status ? 'Verified' : 'Pending'}
                        </Badge>
                    </div>
                    <Separator />
                    <div className="flex justify-between items-center">
                        <span className="text-sm font-medium">BSE Registration</span>
                        <div className="text-right">
                             {investor.ucc_code ? (
                                <Badge variant="outline" className="text-blue-600 border-blue-600">{investor.ucc_code}</Badge>
                             ) : (
                                <Badge variant="secondary">Not Registered</Badge>
                             )}
                        </div>
                    </div>
                    {investor.bse_remarks && (
                        <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
                            {investor.bse_remarks}
                        </div>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader>
                    <CardTitle>Relations</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div>
                        <div className="text-sm font-medium text-muted-foreground">Distributor</div>
                        <div>{investor.distributor_name || 'Direct'}</div>
                    </div>
                    <div>
                        <div className="text-sm font-medium text-muted-foreground">Relationship Manager</div>
                        <div>{investor.rm_name || '-'}</div>
                    </div>
                </CardContent>
            </Card>
        </div>

        {/* Main Content Tabs */}
        <div className="md:col-span-2">
            <Tabs defaultValue="profile" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="profile">Profile</TabsTrigger>
                    <TabsTrigger value="bank">Bank Accounts</TabsTrigger>
                    <TabsTrigger value="nominee">Nominees</TabsTrigger>
                    <TabsTrigger value="docs">Documents</TabsTrigger>
                </TabsList>

                <TabsContent value="profile" className="space-y-4 mt-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Personal Information</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">PAN Number</div>
                                    <div>{investor.pan}</div>
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">Date of Birth</div>
                                    <div>{investor.dob || '-'}</div>
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">Mobile</div>
                                    <div>{investor.mobile}</div>
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">Email</div>
                                    <div>{investor.email}</div>
                                </div>
                                <div>
                                    <div className="text-sm font-medium text-muted-foreground">Gender</div>
                                    <div>{investor.gender === 'M' ? 'Male' : investor.gender === 'F' ? 'Female' : 'Other'}</div>
                                </div>
                            </div>
                            <Separator />
                            <div className="space-y-2">
                                <div className="text-sm font-medium text-muted-foreground">Address</div>
                                <div>
                                    {investor.address_1}<br/>
                                    {investor.address_2 && <>{investor.address_2}<br/></>}
                                    {investor.city}, {investor.state} - {investor.pincode}<br/>
                                    {investor.country}
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Tax & Occupation</CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-2 gap-4">
                            <div>
                                <div className="text-sm font-medium text-muted-foreground">Tax Status</div>
                                <div>{investor.tax_status_display}</div>
                            </div>
                            <div>
                                <div className="text-sm font-medium text-muted-foreground">Occupation</div>
                                <div>{investor.occupation_display}</div>
                            </div>
                            <div>
                                <div className="text-sm font-medium text-muted-foreground">Holding Nature</div>
                                <div>{investor.holding_nature_display}</div>
                            </div>
                            <div>
                                <div className="text-sm font-medium text-muted-foreground">KYC Type</div>
                                <div>{investor.kyc_type_display}</div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="bank" className="mt-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Bank Accounts</CardTitle>
                            <CardDescription>Linked bank accounts for transactions.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {investor.bank_accounts.length === 0 ? (
                                <div className="text-center text-muted-foreground py-4">No bank accounts found.</div>
                            ) : (
                                investor.bank_accounts.map((bank) => (
                                    <div key={bank.id} className="border p-4 rounded-lg flex justify-between items-start">
                                        <div>
                                            <div className="font-semibold flex items-center gap-2">
                                                {bank.bank_name}
                                                {bank.is_default && <Badge variant="secondary" className="text-[10px]">Default</Badge>}
                                            </div>
                                            <div className="text-sm text-muted-foreground">{bank.branch_name}</div>
                                            <div className="mt-2 text-sm">
                                                <span className="font-mono bg-muted px-1 rounded">{bank.account_number}</span>
                                                <span className="mx-2 text-muted-foreground">•</span>
                                                <span className="text-muted-foreground">{bank.ifsc_code}</span>
                                            </div>
                                        </div>
                                        <div className="text-right text-sm text-muted-foreground">
                                            {bank.account_type_display}
                                        </div>
                                    </div>
                                ))
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="nominee" className="mt-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Nominees</CardTitle>
                            <CardDescription>Nominee details and allocation.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                             {investor.nominees.length === 0 ? (
                                <div className="text-center text-muted-foreground py-4">No nominees found.</div>
                            ) : (
                                investor.nominees.map((nominee) => (
                                    <div key={nominee.id} className="border p-4 rounded-lg flex justify-between items-center">
                                        <div>
                                            <div className="font-semibold">{nominee.name}</div>
                                            <div className="text-sm text-muted-foreground">{nominee.relationship_display}</div>
                                            {nominee.guardian_name && (
                                                <div className="text-xs text-muted-foreground mt-1">Guardian: {nominee.guardian_name}</div>
                                            )}
                                        </div>
                                        <div className="text-right">
                                            <div className="text-2xl font-bold">{nominee.percentage}%</div>
                                            <div className="text-xs text-muted-foreground">Allocation</div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="docs" className="mt-4">
                     <Card>
                        <CardHeader>
                            <CardTitle>Documents</CardTitle>
                            <CardDescription>KYC and other uploaded documents.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                             {investor.documents.length === 0 ? (
                                <div className="text-center text-muted-foreground py-4">No documents found.</div>
                            ) : (
                                investor.documents.map((doc) => (
                                    <div key={doc.id} className="flex items-center justify-between border p-3 rounded-lg hover:bg-muted/50 transition-colors">
                                        <div className="flex items-center gap-3">
                                            <div className="bg-primary/10 p-2 rounded">
                                                <Download className="h-4 w-4 text-primary" />
                                            </div>
                                            <div>
                                                <div className="font-medium">{doc.document_type_display}</div>
                                                <div className="text-xs text-muted-foreground">
                                                    Uploaded on {new Date(doc.uploaded_at).toLocaleDateString()}
                                                </div>
                                            </div>
                                        </div>
                                        {doc.file_url && (
                                            <a href={doc.file_url} target="_blank" rel="noreferrer">
                                                <Button variant="ghost" size="sm">
                                                    <ExternalLink className="h-4 w-4" />
                                                </Button>
                                            </a>
                                        )}
                                    </div>
                                ))
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
      </div>
    </div>
  );
};

export default InvestorDetail;
