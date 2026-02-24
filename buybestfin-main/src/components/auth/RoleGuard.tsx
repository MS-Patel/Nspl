import { Navigate, useOutletContext, useLocation } from "react-router-dom";
import { User } from "@/types/auth";

interface DashboardContext {
  user: User;
}

interface RoleGuardProps {
  allowedRoles: string[];
  children: React.ReactNode;
}

const RoleGuard = ({ allowedRoles, children }: RoleGuardProps) => {
  const context = useOutletContext<DashboardContext>();
  const location = useLocation();

  if (!context || !context.user) {
    // If user is not yet loaded, DashboardLayout should handle it (loading state).
    // If it's loaded and null, DashboardLayout redirects.
    // So this case should ideally not happen if DashboardLayout logic is sound.
    return null;
  }

  const userRole = context.user.role;

  if (!allowedRoles.includes(userRole)) {
    // Redirect to their allowed dashboard
    if (userRole === 'ADMIN') return <Navigate to="/dashboard/admin" replace />;
    if (userRole === 'RM') return <Navigate to="/dashboard/rm" replace />;
    if (userRole === 'DISTRIBUTOR') return <Navigate to="/dashboard/distributor" replace />;
    if (userRole === 'INVESTOR') return <Navigate to="/dashboard/investor" replace />;
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default RoleGuard;
