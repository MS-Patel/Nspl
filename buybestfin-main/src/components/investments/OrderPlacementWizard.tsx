import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';

interface Scheme {
  id: number;
  name: string;
  scheme_code: string;
  min_purchase_amount: number;
}

interface Investor {
  id: number;
  user__username: string;
  pan: string;
}

const OrderPlacementWizard = () => {
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [loading, setLoading] = useState(false);

  // Form States
  const [selectedInvestor, setSelectedInvestor] = useState<string>('');
  const [selectedScheme, setSelectedScheme] = useState<string>('');
  const [amount, setAmount] = useState<string>('');
  const [units, setUnits] = useState<string>('');

  // SIP Specific
  const [sipFrequency, setSipFrequency] = useState('MONTHLY');
  const [sipStartDate, setSipStartDate] = useState('');
  const [sipInstallments, setSipInstallments] = useState('12');
  const [selectedMandate, setSelectedMandate] = useState('');
  const [mandates, setMandates] = useState<any[]>([]);

  useEffect(() => {
    // Fetch Metadata
    const fetchMetadata = async () => {
      try {
        const data: any = await api.get('/api/metadata/?fetch_schemes=true');
        if (data.schemes) setSchemes(data.schemes);

        // Fetch Investors (Assuming current user is Admin/RM/Distributor, if Investor, this might return empty or just self)
        // For now, let's try to fetch from legacy or assume user context
        if (data.investors) {
             setInvestors(data.investors);
        } else {
             // Fallback: Fetch from a dedicated investor list endpoint if available
             // For now, we might need to rely on the user typing ID or select from a list if they are Admin
        }
      } catch (error) {
        console.error("Failed to load metadata", error);
      }
    };
    fetchMetadata();
  }, []);

  useEffect(() => {
      if (selectedInvestor) {
          // Fetch mandates for this investor
          const fetchMandates = async () => {
              try {
                  const data: any = await api.get(`/api/metadata/?investor_id=${selectedInvestor}`);
                  if (data.mandates) setMandates(data.mandates);
              } catch (e) {
                  console.error(e);
              }
          }
          fetchMandates();
      }
  }, [selectedInvestor]);

  const handleSubmit = async (type: string) => {
    setLoading(true);
    try {
      const payload: any = {
        transaction_type: type,
        investor_id: selectedInvestor,
        scheme_id: selectedScheme,
        amount: parseFloat(amount) || 0,
        units: parseFloat(units) || 0,
      };

      if (type === 'SIP') {
          payload.sip_frequency = sipFrequency;
          payload.sip_start_date = sipStartDate;
          payload.sip_installments = parseInt(sipInstallments);
          payload.mandate_id = selectedMandate;
      }

      const response: any = await api.post('/api/orders/create/', payload);

      if (response.status === 'success') {
          toast.success(response.message);
          // Reset Form
          setAmount('');
      } else {
          toast.error(response.message || "Order Failed");
      }

    } catch (error: any) {
        toast.error(error.response?.data?.message || "Order Submission Failed");
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
        <div className="mb-6 grid grid-cols-2 gap-4">
             <div>
                <Label>Select Investor</Label>
                <Select onValueChange={setSelectedInvestor} value={selectedInvestor}>
                    <SelectTrigger>
                        <SelectValue placeholder="Select Investor" />
                    </SelectTrigger>
                    <SelectContent>
                        {investors.map((inv) => (
                            <SelectItem key={inv.id} value={inv.id.toString()}>
                                {inv.user__username} ({inv.pan})
                            </SelectItem>
                        ))}
                         {investors.length === 0 && <SelectItem value="self">Myself (If Investor)</SelectItem>}
                    </SelectContent>
                </Select>
             </div>
        </div>

      <Tabs defaultValue="lumpsum" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="lumpsum">Lumpsum</TabsTrigger>
          <TabsTrigger value="sip">SIP</TabsTrigger>
          <TabsTrigger value="redeem">Redeem</TabsTrigger>
          <TabsTrigger value="switch">Switch</TabsTrigger>
        </TabsList>

        {/* LUMPSUM TAB */}
        <TabsContent value="lumpsum">
          <Card>
            <CardHeader>
              <CardTitle>New Purchase</CardTitle>
              <CardDescription>Make a one-time investment.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1">
                <Label>Scheme</Label>
                 <Select onValueChange={setSelectedScheme} value={selectedScheme}>
                    <SelectTrigger>
                        <SelectValue placeholder="Select Scheme" />
                    </SelectTrigger>
                    <SelectContent>
                        {schemes.slice(0, 100).map((s) => (
                            <SelectItem key={s.id} value={s.id.toString()}>
                                {s.name}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>Amount</Label>
                <Input type="number" placeholder="Enter Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={() => handleSubmit('P')} disabled={loading}>
                {loading ? 'Processing...' : 'Place Order'}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* SIP TAB */}
        <TabsContent value="sip">
          <Card>
            <CardHeader>
              <CardTitle>Start SIP</CardTitle>
              <CardDescription>Regular investment plan.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-1">
                <Label>Scheme</Label>
                 <Select onValueChange={setSelectedScheme} value={selectedScheme}>
                    <SelectTrigger>
                        <SelectValue placeholder="Select Scheme" />
                    </SelectTrigger>
                    <SelectContent>
                        {schemes.filter(s => s.min_purchase_amount > 0).slice(0, 100).map((s) => (
                            <SelectItem key={s.id} value={s.id.toString()}>
                                {s.name}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <Label>Amount</Label>
                    <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label>Frequency</Label>
                    <Select value={sipFrequency} onValueChange={setSipFrequency}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="MONTHLY">Monthly</SelectItem>
                            <SelectItem value="WEEKLY">Weekly</SelectItem>
                        </SelectContent>
                    </Select>
                  </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <Label>Start Date</Label>
                    <Input type="date" value={sipStartDate} onChange={(e) => setSipStartDate(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label>Installments</Label>
                    <Input type="number" value={sipInstallments} onChange={(e) => setSipInstallments(e.target.value)} />
                  </div>
              </div>
               <div className="space-y-1">
                <Label>Mandate</Label>
                 <Select onValueChange={setSelectedMandate} value={selectedMandate}>
                    <SelectTrigger>
                        <SelectValue placeholder="Select Approved Mandate" />
                    </SelectTrigger>
                    <SelectContent>
                        {mandates.map((m) => (
                            <SelectItem key={m.id} value={m.id.toString()}>
                                {m.mandate_id} - ₹{m.amount_limit} ({m.bank_account__bank_name})
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={() => handleSubmit('SIP')} disabled={loading}>
                {loading ? 'Processing...' : 'Register SIP'}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* REDEEM TAB */}
        <TabsContent value="redeem">
          <Card>
            <CardHeader>
              <CardTitle>Redeem</CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">Select a holding from your portfolio to redeem.</p>
                {/* Simplified for now */}
            </CardContent>
             <CardFooter>
              <Button disabled>Select Holding from Portfolio</Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* SWITCH TAB */}
        <TabsContent value="switch">
            <Card>
            <CardHeader>
              <CardTitle>Switch</CardTitle>
            </CardHeader>
            <CardContent>
                 <p className="text-muted-foreground">Select a holding from your portfolio to switch.</p>
            </CardContent>
            <CardFooter>
              <Button disabled>Select Holding from Portfolio</Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default OrderPlacementWizard;
