import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Login from "./pages/Login";
import Calculator from "./pages/Calculator";
import Explorer from "./pages/Explorer";
import RiskProfile from "./pages/RiskProfile";
import GoalCalculator from "./pages/GoalCalculator";
import FundKnowledge from "./pages/FundKnowledge";
import Products from "./pages/Products";
import UnlistedEquities from "./pages/UnlistedEquities";
import LiveMarket from "./pages/LiveMarket";
import NotFound from "./pages/NotFound";
import ChatWidget from "./components/ChatWidget";
import DashboardLayout from "@/components/layout/DashboardLayout";
import AdminDashboard from "@/pages/dashboard/AdminDashboard";
import RMDashboard from "@/pages/dashboard/RMDashboard";
import DistributorDashboard from "@/pages/dashboard/DistributorDashboard";
import InvestorDashboard from "@/pages/dashboard/InvestorDashboard";
import InvestorList from "@/pages/dashboard/investors/InvestorList";
import CreateInvestor from "@/pages/dashboard/investors/CreateInvestor";
import InvestorDetail from "@/pages/dashboard/investors/InvestorDetail";

// Investment Pages
import InvestPage from "@/pages/dashboard/investments/InvestPage";
import OrderList from "@/pages/dashboard/investments/OrderList";
import SIPList from "@/pages/dashboard/investments/SIPList";
import MandateList from "@/pages/dashboard/investments/MandateList";

// Portfolio Pages
import Holdings from "@/pages/dashboard/portfolio/Holdings";
import Analytics from "@/pages/dashboard/portfolio/Analytics";

// Settings Pages
import Profile from "@/pages/dashboard/settings/Profile";
import Security from "@/pages/dashboard/settings/Security";
import Banks from "@/pages/dashboard/settings/Banks";
import Nominees from "@/pages/dashboard/settings/Nominees";

// Admin Pages
import Reconciliation from "@/pages/dashboard/admin/Reconciliation";
import Reports from "@/pages/dashboard/admin/Reports";

import RoleGuard from "@/components/auth/RoleGuard";

// User Management
import RMList from "@/pages/dashboard/users/rm/RMList";
import RMForm from "@/pages/dashboard/users/rm/RMForm";
import DistributorList from "@/pages/dashboard/users/distributor/DistributorList";
import DistributorForm from "@/pages/dashboard/users/distributor/DistributorForm";

// Product Management
import AMCList from "@/pages/dashboard/products/AMCList";
import SchemeExplorer from "@/pages/dashboard/products/SchemeExplorer";
import UploadCenter from "@/pages/dashboard/products/UploadCenter";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter basename="/static">
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/login" element={<Login />} />
          <Route path="/calculator" element={<Calculator />} />
          <Route path="/goal-calculator" element={<GoalCalculator />} />
          <Route path="/explorer" element={<Explorer />} />
          <Route path="/risk-profile" element={<RiskProfile />} />
          <Route path="/fund-knowledge" element={<FundKnowledge />} />
          <Route path="/products" element={<Products />} />
          <Route path="/unlisted-equities" element={<UnlistedEquities />} />
          <Route path="/live-market" element={<LiveMarket />} />

          {/* Dashboard Routes with Role Guards */}
          <Route path="/dashboard" element={<DashboardLayout />}>
            <Route path="admin" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <AdminDashboard />
              </RoleGuard>
            } />
            <Route path="rm" element={
              <RoleGuard allowedRoles={['RM', 'ADMIN']}>
                <RMDashboard />
              </RoleGuard>
            } />
            <Route path="distributor" element={
              <RoleGuard allowedRoles={['DISTRIBUTOR', 'ADMIN', 'RM']}>
                <DistributorDashboard />
              </RoleGuard>
            } />
            <Route path="investor" element={
              <RoleGuard allowedRoles={['INVESTOR', 'ADMIN', 'RM', 'DISTRIBUTOR']}>
                <InvestorDashboard />
              </RoleGuard>
            } />
            <Route path="investors" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR']}>
                <InvestorList />
              </RoleGuard>
            } />
            <Route path="investors/new" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR']}>
                <CreateInvestor />
              </RoleGuard>
            } />
            <Route path="investors/:id" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR']}>
                <InvestorDetail />
              </RoleGuard>
            } />

            {/* RM Management */}
            <Route path="rms" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <RMList />
              </RoleGuard>
            } />
            <Route path="rms/new" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <RMForm />
              </RoleGuard>
            } />
            <Route path="rms/:id" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <RMForm />
              </RoleGuard>
            } />

            {/* Distributor Management */}
            <Route path="distributors" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM']}>
                <DistributorList />
              </RoleGuard>
            } />
            <Route path="distributors/new" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM']}>
                <DistributorForm />
              </RoleGuard>
            } />
            <Route path="distributors/:id" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM']}>
                <DistributorForm />
              </RoleGuard>
            } />

            {/* Product Management */}
            <Route path="products/amc" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <AMCList />
              </RoleGuard>
            } />
            <Route path="products/schemes" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <SchemeExplorer />
              </RoleGuard>
            } />
            <Route path="products/upload" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <UploadCenter />
              </RoleGuard>
            } />

            {/* Investment Routes */}
            <Route path="investments/invest" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR', 'INVESTOR']}>
                <InvestPage />
              </RoleGuard>
            } />
            <Route path="investments/orders" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR', 'INVESTOR']}>
                <OrderList />
              </RoleGuard>
            } />
            <Route path="investments/sips" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR', 'INVESTOR']}>
                <SIPList />
              </RoleGuard>
            } />
            <Route path="investments/mandates" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR', 'INVESTOR']}>
                <MandateList />
              </RoleGuard>
            } />

            {/* Portfolio Routes */}
            <Route path="portfolio/holdings" element={
              <RoleGuard allowedRoles={['INVESTOR', 'ADMIN', 'RM']}>
                <Holdings />
              </RoleGuard>
            } />
            <Route path="portfolio/analytics" element={
              <RoleGuard allowedRoles={['INVESTOR', 'ADMIN', 'RM']}>
                <Analytics />
              </RoleGuard>
            } />

            {/* Settings Routes */}
            <Route path="settings/profile" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR', 'INVESTOR']}>
                <Profile />
              </RoleGuard>
            } />
            <Route path="settings/security" element={
              <RoleGuard allowedRoles={['ADMIN', 'RM', 'DISTRIBUTOR', 'INVESTOR']}>
                <Security />
              </RoleGuard>
            } />
            <Route path="settings/banks" element={
              <RoleGuard allowedRoles={['INVESTOR', 'ADMIN', 'RM']}>
                <Banks />
              </RoleGuard>
            } />
            <Route path="settings/nominees" element={
              <RoleGuard allowedRoles={['INVESTOR', 'ADMIN', 'RM']}>
                <Nominees />
              </RoleGuard>
            } />

            {/* Admin Operations */}
            <Route path="admin/reconciliation" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <Reconciliation />
              </RoleGuard>
            } />
            <Route path="admin/reports" element={
              <RoleGuard allowedRoles={['ADMIN']}>
                <Reports />
              </RoleGuard>
            } />
          </Route>

          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
        <ChatWidget />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
