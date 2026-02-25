import { useNavigate } from 'react-router-dom';
import OrderPlacementWizard from '@/components/investments/OrderPlacementWizard';

const InvestPage = () => {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Invest</h1>
        <p className="text-muted-foreground">Start a new investment journey.</p>
      </div>
      <OrderPlacementWizard />
    </div>
  );
};

export default InvestPage;
