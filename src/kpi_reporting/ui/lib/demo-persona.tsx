/**
 * Demo persona switcher — P&L Manager (Jordan Lee), General Manager (Alex Morgan)
 * or CFO (Sam Carter). The names match the seeded userbase in notebook 01 / mock_data.py.
 *
 * The reporting flow: the P&L manager drafts and submits the region's KPI
 * justifications, the GM reviews and approves them (or sends them back), and the
 * CFO consolidates all regions.
 *
 * Stored in sessionStorage so it survives page navigation but resets on tab close.
 * Does NOT touch the real auth layer — purely for demo purposes.
 */
import { createContext, useContext, useState, type ReactNode } from "react";

export type DemoPersonaId = "pnl" | "gm" | "cfo";

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
  pnl: {
    id: "pnl",
    name: "Jordan Lee",
    initials: "JL",
    role: "P&L Manager",
    department: "Region North",
    avatar_color: "bg-violet-600",
    allowed_routes: ["/", "/kpi-submission"],
  },
  gm: {
    id: "gm",
    name: "Alex Morgan",
    initials: "AM",
    role: "General Manager",
    department: "Region North",
    avatar_color: "bg-blue-600",
    allowed_routes: ["/", "/kpi-review"],
  },
  cfo: {
    id: "cfo",
    name: "Sam Carter",
    initials: "SC",
    role: "Chief Financial Officer",
    department: "Bricks Co — Group Finance",
    avatar_color: "bg-emerald-600",
    allowed_routes: ["/", "/executive-dashboard", "/analytics-dashboard", "/risk-report"],
  },
};

/** Personas in the order of the reporting flow (used by the switcher). */
export const PERSONA_ORDER: DemoPersonaId[] = ["pnl", "gm", "cfo"];

const STORAGE_KEY = "demo_persona";

export function isPersonaId(value: string | null): value is DemoPersonaId {
  return value === "pnl" || value === "gm" || value === "cfo";
}

interface DemoPersonaContextValue {
  persona: DemoPersona;
  switchPersona: (id: DemoPersonaId) => void;
}

const DemoPersonaContext = createContext<DemoPersonaContextValue | null>(null);

export function DemoPersonaProvider({ children }: { children: ReactNode }) {
  const [personaId, setPersonaId] = useState<DemoPersonaId>(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    return isPersonaId(stored) ? stored : "pnl";
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
