import { Mail, Phone, MapPin } from "lucide-react";
import logo from "@/assets/logo.png";

const Footer = () => {
  return (
    <footer id="contact" className="relative bg-foreground text-background py-16 overflow-hidden">
      {/* Decorative gradient wave */}
      <div className="absolute top-0 left-0 right-0 h-1 gradient-primary" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <img src={logo} alt="BuyBestFin" className="w-10 h-10 rounded-lg" />
              <span className="text-lg font-bold">BuyBestFin</span>
            </div>
            <p className="text-sm opacity-70">
              AMFI Registered Mutual Fund Distributor. ARN: 147231. 
              Your trusted partner for all investment needs.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-4" style={{ fontFamily: 'DM Sans' }}>Services</h4>
            <ul className="space-y-2 text-sm opacity-70">
              <li>Mutual Funds</li>
              <li>Unlisted Equities</li>
              <li>Listed Equities</li>
              <li>Bonds</li>
              <li>Corporate FDs</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4" style={{ fontFamily: 'DM Sans' }}>Quick Links</h4>
            <ul className="space-y-2 text-sm opacity-70">
              <li>About Us</li>
              <li>Customer Login</li>
              <li>Partner Login</li>
              <li>Privacy Policy</li>
              <li>Terms & Conditions</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4" style={{ fontFamily: 'DM Sans' }}>Contact</h4>
            <div className="space-y-3 text-sm opacity-70">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 shrink-0" />
                <span>info@buybestfin.com</span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 shrink-0" />
                <span>+91-9315494820</span>
              </div>
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 shrink-0 mt-0.5" />
                <span>121, Fortune Tower, Dalal Street, Sayajiganj Vadodara Gujarat 390020 India</span>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-background/10 mt-12 pt-8">
          <p className="text-xs opacity-50 text-center">
            © {new Date().getFullYear()} BuyBestFin. All rights reserved. | 
            Mutual Fund investments are subject to market risks. Please read all scheme related documents carefully before investing. | 
            ARN: 147231
          </p>
        </div>
      </div>
    </footer>);

};

export default Footer;