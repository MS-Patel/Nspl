import SIPListComponent from '@/components/investments/SIPList';

const SIPList = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Systematic Investment Plans (SIPs)</h2>
      </div>
      <SIPListComponent />
    </div>
  );
};

export default SIPList;
