/**
 * Home page — personalised welcome + tasks of the day.
 * Shown to both GM and CFO as their landing page.
 */
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useDemoPersona, PERSONAS, type DemoPersonaId } from "@/lib/demo-persona";
import { useGetTasks } from "@/lib/api";
import { CheckCircle2, Circle, Clock, ArrowRight, RefreshCw, Users, ShieldAlert, LayoutDashboard } from "lucide-react";

// TaskAction isn't in the generated types yet — augment locally
interface TaskAction { label: string; route: string; variant: string; }
interface TaskItemWithActions { actions?: TaskAction[] }
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/_sidebar/home")({
  component: () => <HomePage />,
});

function StatusIcon({ status }: { status: string }) {
  if (status === "done") return <CheckCircle2 size={18} className="text-green-500 shrink-0" />;
  if (status === "in_progress") return <Clock size={18} className="text-amber-500 shrink-0" />;
  return <Circle size={18} className="text-muted-foreground shrink-0" />;
}

function StatusBadge({ status }: { status: string }) {
  if (status === "done") return <Badge variant="outline" className="text-green-600 border-green-300 bg-green-50">Complete</Badge>;
  if (status === "in_progress") return <Badge variant="outline" className="text-amber-600 border-amber-300 bg-amber-50">In Progress</Badge>;
  return <Badge variant="outline" className="text-muted-foreground">Pending</Badge>;
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function HomePage() {
  const { persona, switchPersona } = useDemoPersona();
  const navigate = useNavigate();

  const otherPersonaId: DemoPersonaId = persona.id === "gm" ? "cfo" : "gm";
  const otherPersona = PERSONAS[otherPersonaId];

  const { data, isLoading, refetch } = useGetTasks({
    params: { persona: persona.id },
    query: { staleTime: 30_000 },
  });

  const tasks = data?.data?.tasks ?? [];
  const activePeriod = data?.data?.period ?? "";
  const pendingCount = tasks.filter(t => t.status !== "done").length;

  const handleTaskClick = (route: string | null | undefined, period?: string | null) => {
    if (!route) return;
    if (route === "/executive-dashboard" && period) {
      navigate({ to: "/executive-dashboard", search: { period } });
    } else if (route === "/risk-report") {
      navigate({ to: "/risk-report", search: { period: period ?? undefined } });
    } else {
      navigate({ to: route as "/" });
    }
  };

  const handleSwitch = () => {
    switchPersona(otherPersonaId);
    navigate({ to: "/" });
  };

  return (
    <div className="flex flex-col flex-1 overflow-auto p-6 gap-6 max-w-3xl mx-auto w-full">

      {/* Welcome header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className={`w-14 h-14 rounded-full ${persona.avatar_color} flex items-center justify-center text-white font-bold text-lg shrink-0`}>
            {persona.initials}
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              {getGreeting()}, {persona.name.split(" ")[0]}
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {persona.role} · {persona.department}
            </p>
          </div>
        </div>

        {/* Switch user button */}
        <Button
          variant="outline"
          size="sm"
          className="gap-2 shrink-0 mt-1"
          onClick={handleSwitch}
        >
          <Users size={14} />
          Log in as {otherPersona.name.split(" ")[0]}
        </Button>
      </div>

      {/* Task summary */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-medium text-foreground">
            {pendingCount > 0
              ? `You have ${pendingCount} task${pendingCount > 1 ? "s" : ""} to complete`
              : "All tasks complete — well done!"}
          </h2>
          {activePeriod && (
            <p className="text-xs text-muted-foreground mt-0.5">Current reporting period: {activePeriod}</p>
          )}
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground" onClick={() => refetch()}>
          <RefreshCw size={13} />
        </Button>
      </div>

      {/* Task cards */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-muted-foreground text-sm">
            No tasks found for your profile.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {tasks.map(task => {
            const actions = (task as unknown as TaskItemWithActions).actions ?? [];
            return (
            <Card
              key={task.id}
              className={`transition-all border ${
                task.status === "done" ? "opacity-70" : "hover:shadow-md hover:border-primary/40"
              }`}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <StatusIcon status={task.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm text-foreground">{task.title}</span>
                      <StatusBadge status={task.status} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{task.description}</p>

                    {/* GM bar: unjustified KPIs */}
                    {task.count != null && task.total != null && task.status !== "done" && (
                      <div className="mt-2 space-y-1">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{task.total - task.count} of {task.total} justified</span>
                          <span>{Math.round(((task.total - task.count) / task.total) * 100)}%</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                          <div className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${((task.total - task.count) / task.total) * 100}%` }} />
                        </div>
                      </div>
                    )}

                    {/* CFO bars: locked + sentiment */}
                    {task.unlocked_count != null && task.total != null && (
                      <div className="mt-2 space-y-1.5">
                        <div>
                          <div className="flex items-center justify-between text-xs text-muted-foreground mb-0.5">
                            <span>Locked in</span>
                            <span>{task.total - task.unlocked_count}/{task.total}</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                            <div className="h-full rounded-full bg-primary transition-all"
                              style={{ width: `${((task.total - task.unlocked_count) / task.total) * 100}%` }} />
                          </div>
                        </div>
                        {task.negative_count != null && (
                          <div>
                            <div className="flex items-center justify-between text-xs text-muted-foreground mb-0.5">
                              <span>Cautious / negative sentiment</span>
                              <span>{task.negative_count}/{task.total}</span>
                            </div>
                            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                              <div className="h-full rounded-full bg-amber-400 transition-all"
                                style={{ width: `${(task.negative_count / task.total) * 100}%` }} />
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Action buttons */}
                    {actions.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        {actions.map((action, i) => (
<Button
                            key={i}
                            size="sm"
                            variant={action.variant === "outline" ? "outline" : "default"}
                            className={`h-7 text-xs gap-1.5 ${action.route === "/risk-report" && action.variant !== "outline" ? "bg-amber-500 hover:bg-amber-600 text-white border-0" : ""}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleTaskClick(action.route, task.period);
                            }}
                          >
                            {action.route === "/risk-report"
                              ? <ShieldAlert size={11} />
                              : <LayoutDashboard size={11} />}
                            {action.label}
                          </Button>
                        ))}
                      </div>
                    )}

                    {/* GM fallback arrow (no actions) */}
                    {actions.length === 0 && task.status !== "done" && task.route && (
                      <Button
                        size="sm" variant="outline"
                        className="h-7 text-xs gap-1.5 mt-3"
                        onClick={() => handleTaskClick(task.route, task.period)}
                      >
                        <ArrowRight size={11} /> Go to KPI Reporting
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
            );
          })}
        </div>
      )}

      {/* Role context card */}
      <Card className="bg-muted/30 border-dashed">
        <CardHeader className="pb-2 pt-4">
          <CardTitle className="text-sm font-medium text-muted-foreground">Your access</CardTitle>
        </CardHeader>
        <CardContent className="pb-4 pt-0">
          <p className="text-xs text-muted-foreground leading-relaxed">
            {persona.id === "gm"
              ? "As General Manager, you can submit and manage KPI justifications for your region."
              : "As Chief Financial Officer, you have read access to all KPI submissions across all regions and can generate executive reports."}
          </p>
        </CardContent>
      </Card>

    </div>
  );
}
