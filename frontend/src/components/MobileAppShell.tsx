import type { ReactNode } from "react";

import { HomeReturnLink } from "./HomeReturnLink";

type MobileAppShellProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  bottom?: ReactNode;
  className?: string;
  showHomeReturn?: boolean;
};

export function MobileAppShell({
  title,
  subtitle,
  children,
  bottom,
  className = "",
  showHomeReturn = false
}: MobileAppShellProps) {
  return (
    <div className={`mobile-shell ${bottom ? "has-bottom-actions" : ""} ${className}`.trim()}>
      <header className="app-header">
        {showHomeReturn ? <HomeReturnLink /> : null}
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </header>
      <main className="app-content">{children}</main>
      {bottom ? <nav className="bottom-actions">{bottom}</nav> : null}
    </div>
  );
}
