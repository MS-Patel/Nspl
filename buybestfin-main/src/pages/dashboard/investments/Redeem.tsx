import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import OrderPlacementWizard from '@/components/investments/OrderPlacementWizard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const Redeem = () => {
  const { holdingId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [initialValues, setInitialValues] = useState<any>(null);

  useEffect(() => {
    const fetchHolding = async () => {
      if (!holdingId) {
          setLoading(false);
          return;
      }

      try {
        const holdings: any = await api.get('/api/holdings/');
        const holding = holdings.find((h: any) => h.id.toString() === holdingId);

        if (holding) {
          setInitialValues({
            transaction_type: 'R',
            investor_id: holding.investor_id ? holding.investor_id.toString() : '',
            scheme_id: holding.scheme_id ? holding.scheme_id.toString() : '',
            folio_number: holding.folio,
            all_redeem: false,
            amount: '',
            units: ''
          });
        } else {
          toast.error("Holding not found");
          navigate('/dashboard/portfolio/holdings');
        }
      } catch (error) {
        console.error("Failed to fetch holding details", error);
        toast.error("Failed to load holding details");
      } finally {
        setLoading(false);
      }
    };

    fetchHolding();
  }, [holdingId, navigate]);

  if (loading) {
      return <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard/portfolio/holdings')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h2 className="text-3xl font-bold tracking-tight">Redeem Investment</h2>
      </div>

      {initialValues ? (
        <OrderPlacementWizard initialTab="redeem" initialValues={initialValues} />
      ) : (
        <Card>
            <CardHeader>
                <CardTitle>Error</CardTitle>
            </CardHeader>
            <CardContent>
                <p>Could not load redemption details.</p>
                <Button className="mt-4" onClick={() => navigate('/dashboard/portfolio/holdings')}>Go Back</Button>
            </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Redeem;
