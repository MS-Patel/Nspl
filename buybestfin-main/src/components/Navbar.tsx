import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import logo from "@/assets/logo.png";

const navLinks = [
{ to: "/products", label: "Our Products" },
{ to: "/live-market", label: "Live Market" },
{ to: "/explorer", label: "Explore Funds" },
{ to: "/unlisted-equities", label: "Unlisted Equities" },
{ to: "/calculator", label: "SIP Calculator" },
{ to: "/risk-profile", label: "Risk Analyzer" }];


const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-card/80 backdrop-blur-lg border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center gap-2">
            <img src={logo} alt="BuyBestFin Logo" className="w-10 h-10 rounded-lg" />
            <div>
              <span className="text-lg font-bold gradient-text" style={{ fontFamily: 'DM Sans' }}>BuyBestFin</span>
              <p className="text-[10px] text-muted-foreground leading-none">By Navinchandra Securities
(ARN: 147231)</p>
            </div>
          </Link>

          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => <Link key={link.to} to={link.to} className="text-sm font-medium text-muted-foreground hover:text-primary transition-colors relative group">
                {link.label}
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 gradient-primary rounded-full transition-all duration-300 group-hover:w-full" />
              </Link>
            )}
            <Link to="/login">
              <Button size="sm" className="gradient-primary border-0 text-white hover:opacity-90 transition-opacity">Login / Register</Button>
            </Link>
          </div>

          <button className="md:hidden" onClick={() => setIsOpen(!isOpen)}>
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {isOpen &&
        <div className="md:hidden py-4 space-y-3 border-t border-border animate-fade-up">
            {navLinks.map((link) =>
          <Link key={link.to} to={link.to} className="block text-sm font-medium text-muted-foreground hover:text-primary transition-colors" onClick={() => setIsOpen(false)}>
                {link.label}
              </Link>
          )}
            <Link to="/login" onClick={() => setIsOpen(false)}>
              <Button size="sm" className="w-full gradient-primary border-0 text-white">Login / Register</Button>
            </Link>
          </div>
        }
      </div>
    </nav>);

};

export default Navbar;