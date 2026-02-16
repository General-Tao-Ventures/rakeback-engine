import { Link, Outlet, useLocation } from "react-router";
import { cn } from "./ui/utils";
import {
  LayoutGrid,
  Database,
  FileText,
  RefreshCw,
  Users,
  AlertTriangle,
  Settings,
  Code,
} from "lucide-react";
import { Toaster } from "./ui/sonner";

const navigation = [
  { name: "System Overview", href: "/", icon: LayoutGrid },
  {
    name: "Block Attribution",
    href: "/block-attribution",
    icon: Database,
  },
  {
    name: "Conversion Events",
    href: "/conversion-events",
    icon: RefreshCw,
  },
  {
    name: "Partner Ledger",
    href: "/partner-ledger",
    icon: FileText,
  },
  {
    name: "Partner Management",
    href: "/partner-management",
    icon: Settings,
  },
  {
    name: "Data Completeness",
    href: "/data-completeness",
    icon: AlertTriangle,
  },
  {
    name: "API Settings",
    href: "/api-settings",
    icon: Code,
  },
];

export function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-semibold tracking-tight text-zinc-50">
                Bittensor Attribution Engine
              </h1>
              <p className="text-sm text-zinc-400">
                Block-by-block yield tracking and partner rakeback system
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500"></div>
                <span>System Operational</span>
              </div>
              <span className="text-zinc-700">•</span>
              <span>Last sync: 2m ago</span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="border-b border-zinc-800 bg-zinc-900/30">
        <div className="px-6">
          <div className="flex gap-1">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive =
                location.pathname === item.href ||
                (item.href !== "/" &&
                  location.pathname.startsWith(item.href));

              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-2 px-4 py-3 text-sm transition-colors border-b-2",
                    isActive
                      ? "border-zinc-50 text-zinc-50"
                      : "border-transparent text-zinc-400 hover:text-zinc-200"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="px-6 py-6">
        <Outlet />
      </main>

      <Toaster />
    </div>
  );
}