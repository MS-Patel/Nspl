import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Menu, X, LogOut, User as UserIcon } from "lucide-react";
import logo from "@/assets/logo.png";
import { User } from "@/types/auth";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

interface DashboardNavbarProps {
  user: User;
}

const DashboardNavbar = ({ user }: DashboardNavbarProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const getMenuItems = () => {
    const items = [
      {
        title: "Dashboard",
        url: `/dashboard/${user.role.toLowerCase()}`,
      },
    ];

    if (user.role === 'ADMIN') {
        items.push({
            title: "RMs",
            url: "/dashboard/rms",
        });
    }

    if (user.role === 'ADMIN' || user.role === 'RM') {
        items.push({
            title: "Distributors",
            url: "/dashboard/distributors",
        });
    }

    if (user.role === 'ADMIN' || user.role === 'RM' || user.role === 'DISTRIBUTOR') {
        items.push({
            title: "Investors",
            url: "/dashboard/investors",
        });
    }

    // Add public links accessible from dashboard? Maybe not to clutter.
    // Let's stick to dashboard specific links.

    return items;
  };

  const menuItems = getMenuItems();

  const handleLogout = () => {
    window.location.href = '/users/logout/';
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-card/80 backdrop-blur-lg border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo Section */}
          <Link to="/" className="flex items-center gap-2">
            <img src={logo} alt="BuyBestFin Logo" className="w-10 h-10 rounded-lg" />
            <div>
              <span className="text-lg font-bold gradient-text" style={{ fontFamily: 'DM Sans' }}>BuyBestFin</span>
              <p className="text-[10px] text-muted-foreground leading-none">
                {user.role} Portal
              </p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            {menuItems.map((item) => {
              const isActive = location.pathname.startsWith(item.url);
              return item.url.startsWith('/dashboard') ? (
                <Link
                  key={item.url}
                  to={item.url}
                  className={`text-sm font-medium transition-colors relative group ${isActive ? 'text-primary' : 'text-muted-foreground hover:text-primary'}`}
                >
                  {item.title}
                  <span className={`absolute -bottom-1 left-0 h-0.5 gradient-primary rounded-full transition-all duration-300 ${isActive ? 'w-full' : 'w-0 group-hover:w-full'}`} />
                </Link>
              ) : (
                <a
                  key={item.url}
                  href={item.url}
                  className={`text-sm font-medium transition-colors relative group ${isActive ? 'text-primary' : 'text-muted-foreground hover:text-primary'}`}
                >
                  {item.title}
                  <span className={`absolute -bottom-1 left-0 h-0.5 gradient-primary rounded-full transition-all duration-300 ${isActive ? 'w-full' : 'w-0 group-hover:w-full'}`} />
                </a>
              );
            })}

            {/* Profile Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback>{user.username.slice(0, 2).toUpperCase()}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56" align="end" forceMount>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{user.name || user.username}</p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <a href="/users/profile/">
                    <UserIcon className="mr-2 h-4 w-4" />
                    <span>Profile</span>
                  </a>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Mobile Menu Button */}
          <button className="md:hidden" onClick={() => setIsOpen(!isOpen)}>
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden py-4 space-y-3 border-t border-border animate-fade-up bg-card">
            {menuItems.map((item) => (
              item.url.startsWith('/dashboard') ? (
                <Link
                  key={item.url}
                  to={item.url}
                  className="block px-4 py-2 text-sm font-medium text-muted-foreground hover:text-primary hover:bg-muted/50 rounded-md transition-colors"
                  onClick={() => setIsOpen(false)}
                >
                  {item.title}
                </Link>
              ) : (
                <a
                  key={item.url}
                  href={item.url}
                  className="block px-4 py-2 text-sm font-medium text-muted-foreground hover:text-primary hover:bg-muted/50 rounded-md transition-colors"
                  onClick={() => setIsOpen(false)}
                >
                  {item.title}
                </a>
              )
            ))}
            <div className="border-t border-border my-2 pt-2">
                <a href="/users/profile/" className="block px-4 py-2 text-sm font-medium text-muted-foreground hover:text-primary">
                    Profile
                </a>
                <button onClick={handleLogout} className="w-full text-left block px-4 py-2 text-sm font-medium text-red-500 hover:bg-red-50 rounded-md">
                    Log out
                </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default DashboardNavbar;
