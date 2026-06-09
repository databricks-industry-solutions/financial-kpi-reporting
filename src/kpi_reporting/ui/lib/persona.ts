import { useGetCurrentUser, type CurrentUser } from "@/lib/api";

export interface Persona {
  deptId: string | null;
  deptName: string | null;
  leadName: string;
  role: string;
  initials: string;
  email: string;
  isExecutive: boolean;
}

function toInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function userToPersona(user: CurrentUser): Persona {
  return {
    deptId: user.department_id,
    deptName: user.department_name,
    leadName: user.name,
    role: user.job_name ?? (user.is_executive ? "Executive" : "Viewer"),
    initials: toInitials(user.name),
    email: user.email,
    isExecutive: user.is_executive,
  };
}

const FALLBACK_PERSONA: Persona = {
  deptId: null,
  deptName: null,
  leadName: "Loading...",
  role: "",
  initials: "??",
  email: "",
  isExecutive: false,
};

export function usePersona() {
  const { data, isLoading } = useGetCurrentUser({ query: { staleTime: Infinity } });
  const persona = data?.data ? userToPersona(data.data) : FALLBACK_PERSONA;
  return { persona, isLoading };
}
