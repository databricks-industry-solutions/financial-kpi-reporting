import { SidebarMenuButton } from "@/components/ui/sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { usePersona } from "@/lib/persona";

export default function SidebarUserFooter() {
  const { persona } = usePersona();

  return (
    <SidebarMenuButton
      size="lg"
      className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
    >
      <Avatar className="h-8 w-8 rounded-lg grayscale">
        <AvatarFallback className="rounded-lg">{persona.initials}</AvatarFallback>
      </Avatar>
      <div className="grid flex-1 text-left text-sm leading-tight">
        <span className="truncate font-medium">{persona.leadName}</span>
        <span className="text-muted-foreground truncate text-xs">
          {persona.isExecutive
            ? persona.role
            : `${persona.deptName} · ${persona.role}`}
        </span>
      </div>
    </SidebarMenuButton>
  );
}
