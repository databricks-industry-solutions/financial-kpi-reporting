import SidebarLayout from "@/components/apx/sidebar-layout";
import { createFileRoute, Link, useLocation } from "@tanstack/react-router";
import { cn } from "@/lib/utils";
import { ClipboardList, LayoutDashboard, BarChart2, Home, ShieldAlert } from "lucide-react";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useDemoPersona } from "@/lib/demo-persona";

export const Route = createFileRoute("/_sidebar")({
  component: () => <Layout />,
});

const ALL_NAV_ITEMS = [
  {
    to: "/home",
    label: "Home",
    icon: <Home size={16} />,
    match: (path: string) => path === "/" || path.startsWith("/home"),
    personas: ["gm", "cfo"],
  },
  {
    to: "/kpi-submission",
    label: "KPI Reporting",
    icon: <ClipboardList size={16} />,
    match: (path: string) => path.startsWith("/kpi-submission"),
    personas: ["gm"],
  },
  {
    to: "/executive-dashboard",
    label: "Executive Overview",
    icon: <LayoutDashboard size={16} />,
    match: (path: string) => path.startsWith("/executive-dashboard"),
    personas: ["cfo"],
  },
  {
    to: "/analytics-dashboard",
    label: "Analytics",
    icon: <BarChart2 size={16} />,
    match: (path: string) => path.startsWith("/analytics-dashboard"),
    personas: ["cfo"],
  },
  {
    to: "/risk-report",
    label: "Risk Report",
    icon: <ShieldAlert size={16} />,
    match: (path: string) => path.startsWith("/risk-report"),
    personas: ["cfo"],
  },
];

function Layout() {
  const location = useLocation();
  const { persona } = useDemoPersona();

  const navItems = ALL_NAV_ITEMS.filter(item => item.personas.includes(persona.id));

  return (
    <SidebarLayout>
      <SidebarGroup>
        <SidebarGroupLabel>Navigation</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            {navItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <Link
                  to={item.to}
                  className={cn(
                    "flex items-center gap-2 p-2 rounded-lg",
                    item.match(location.pathname)
                      ? "bg-ac-blue/10 text-ac-blue font-medium"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  )}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarLayout>
  );
}
