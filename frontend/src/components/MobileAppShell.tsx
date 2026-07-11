import type { ReactNode } from "react";

type MobileAppShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  bottom?: ReactNode;
  className?: string;
};

export function MobileAppShell({
  title,
  subtitle,
  children,
  bottom,
  className = ""
}: MobileAppShellProps) {
  return (
    <div className={`mobile-shell ${bottom ? "has-bottom-actions" : ""} ${className}`.trim()}>
      <header className="app-header">
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </header>
      <main className="app-content">{children}</main>
      {bottom ? <nav className="bottom-actions">{bottom}</nav> : null}
    </div>
  );
}
