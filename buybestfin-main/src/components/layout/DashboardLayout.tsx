import { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { api } from '@/lib/api';
import { User } from '@/types/auth';
import DashboardNavbar from './DashboardNavbar';

export default function DashboardLayout() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const data = await api.get('/api/user/me/');
        setUser(data);
      } catch (error) {
        console.error('Failed to fetch user', error);
        window.location.href = '/login'; // Redirect to login
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  if (!user) {
     return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <DashboardNavbar user={user} />
      <div className="pt-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <Outlet context={{ user }} />
      </div>
    </div>
  );
}
