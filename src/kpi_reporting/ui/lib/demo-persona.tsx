/**
 * Demo persona switcher — General Manager (Alex Morgan) or CFO (Sam Carter).
 * Both names match the seeded userbase in notebook 01 / mock_data.py.
 * Stored in sessionStorage so it survives page navigation but resets on tab close.
 * Does NOT touch the real auth layer — purely for demo purposes.
 */
import { createContext, useContext, useState, type ReactNode } from "react";

export type DemoPersonaId = "gm" | "cfo";

export interface DemoPersona {
  id: DemoPersonaId;
  name: string;
  initials: string;
  role: string;
  department: string;
  avatar_color: string;  // tailwind bg color class
  allowed_routes: string[];  // route prefixes this persona can access
}

export const PERSONAS: Record<DemoPersonaId, DemoPersona> = {
  gm: {
    id: "gm",
    name: "Alex Morgan",
    initials: "AM",
    role: "General Manager",
    department: "Region North",
    avatar_color: "bg-blue-600",
    allowed_routes: ["/", "/kpi-submission"],
  },
  cfo: {
    id: "cfo",
    name: "Sam Carter",
    initials: "SC",
    role: "Chief Financial Officer",
    department: "Bricks Co — Group Finance",
    avatar_color: "bg-emerald-600",
    allowed_routes: ["/", "/executive-dashboard", "/analytics-dashboard"],
  },
};

const STORAGE_KEY = "demo_persona";

interface DemoPersonaContextValue {
  persona: DemoPersona;
  switchPersona: (id: DemoPersonaId) => void;
}

const DemoPersonaContext = createContext<DemoPersonaContextValue | null>(null);

export function DemoPersonaProvider({ children }: { children: ReactNode }) {
  const [personaId, setPersonaId] = useState<DemoPersonaId>(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    return (stored === "gm" || stored === "cfo") ? stored : "gm";
  });

  const switchPersona = (id: DemoPersonaId) => {
    sessionStorage.setItem(STORAGE_KEY, id);
    setPersonaId(id);
  };

  return (
    <DemoPersonaContext.Provider value={{ persona: PERSONAS[personaId], switchPersona }}>
      {children}
    </DemoPersonaContext.Provider>
  );
}

export function useDemoPersona() {
  const ctx = useContext(DemoPersonaContext);
  if (!ctx) throw new Error("useDemoPersona must be used within DemoPersonaProvider");
  return ctx;
}
