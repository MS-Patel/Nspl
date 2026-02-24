import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const RMDashboard = () => {
  const [data, setData] = useState<{message: string} | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await api.get('/api/dashboard/rm/');
        setData(result);
      } catch (error) {
        console.error('Error fetching rm dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="p-8">Loading dashboard...</div>;
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">RM Dashboard</h1>
        <p className="text-muted-foreground">Manage your distributors and investors.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-1">
        <Card>
          <CardHeader>
            <CardTitle>Welcome</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{data?.message || 'Welcome to the Relationship Manager Dashboard.'}</p>
            <p className="mt-4 text-sm text-muted-foreground">
                Features for RMs are currently being migrated. Please access the legacy portal for full functionality if needed.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default RMDashboard;
