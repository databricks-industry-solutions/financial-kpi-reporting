import { SidebarMenuButton } from "@/components/ui/sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useDemoPersona } from "@/lib/demo-persona";

export default function SidebarUserFooter() {
  const { persona } = useDemoPersona();

  return (
    <SidebarMenuButton
      size="lg"
      className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
    >
      <Avatar className="h-8 w-8 rounded-lg">
        <AvatarFallback className={`rounded-lg text-white ${persona.avatar_color}`}>
          {persona.initials}
        </AvatarFallback>
      </Avatar>
      <div className="grid flex-1 text-left text-sm leading-tight">
        <span className="truncate font-medium">{persona.name}</span>
        <span className="text-muted-foreground truncate text-xs">
          {persona.department} · {persona.role}
        </span>
      </div>
    </SidebarMenuButton>
  );
}
