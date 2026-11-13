import { Users } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { PERSONAS, PERSONA_ORDER, isPersonaId, useDemoPersona, type DemoPersonaId } from "@/lib/demo-persona";

/**
 * Demo user switcher. Each option shows the persona's name with their role
 * underneath; the current persona is checked.
 */
export function PersonaSwitcher({ onSwitch }: { onSwitch?: (id: DemoPersonaId) => void }) {
  const { persona, switchPersona } = useDemoPersona();

  const handleChange = (value: string) => {
    if (!isPersonaId(value)) return;
    switchPersona(value);
    onSwitch?.(value);
  };

  return (
    <Select value={persona.id} onValueChange={handleChange}>
      <SelectTrigger aria-label="Switch demo user" className="h-8 w-auto gap-2 text-sm">
        <Users size={14} className="shrink-0" />
        <span>Switch user</span>
      </SelectTrigger>
      <SelectContent align="end">
        {PERSONA_ORDER.map((id) => {
          const p = PERSONAS[id];
          return (
            <SelectItem key={id} value={id} textValue={p.name} className="py-2">
              <span className="flex items-center gap-2.5">
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white ${p.avatar_color}`}
                >
                  {p.initials}
                </span>
                <span className="flex flex-col leading-tight">
                  <span className="font-medium">{p.name}</span>
                  <span className="text-xs text-muted-foreground">{p.role}</span>
                </span>
              </span>
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
}
