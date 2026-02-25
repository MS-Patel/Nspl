import SIPList from '@/components/investments/SIPList';

const SIPsPage = () => {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">SIP Book</h1>
        <p className="text-muted-foreground">Manage your Systematic Investment Plans.</p>
      </div>
      <SIPList />
    </div>
  );
};

export default SIPsPage;
