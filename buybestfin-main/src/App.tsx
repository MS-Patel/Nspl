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

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
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
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
        <ChatWidget />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
