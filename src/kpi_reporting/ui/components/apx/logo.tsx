import { Link } from "@tanstack/react-router";

interface LogoProps {
  to?: string;
  className?: string;
  showText?: boolean;
}

export function Logo({ to = "/", className = "", showText = true }: LogoProps) {
  const content = (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <img src="/logo.svg" alt="Bricks Co" className="h-8 w-8 rounded" />
      {showText && (
        <div className="flex flex-col">
          <span className="font-semibold text-sm leading-tight">Bricks Co</span>
          <span className="text-[10px] text-muted-foreground leading-tight">Financial KPI Reporting</span>
        </div>
      )}
    </div>
  );

  if (to) {
    return (
      <Link to={to} className="hover:opacity-80 transition-opacity">
        {content}
      </Link>
    );
  }

  return content;
}

export default Logo;
