import MandateListComponent from '@/components/investments/MandateList';
import { Button } from '@/components/ui/button';
import { PlusCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const MandateList = () => {
  const navigate = useNavigate();
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Mandates</h2>
        <Button onClick={() => navigate('/dashboard/investments/mandates/new')}>
          <PlusCircle className="mr-2 h-4 w-4" />
          Create Mandate
        </Button>
      </div>
      <MandateListComponent />
    </div>
  );
};

export default MandateList;
