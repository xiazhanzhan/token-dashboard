import type { PropsWithChildren, ReactNode } from "react";

interface PanelProps extends PropsWithChildren {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function Panel({ title, description, action, className = "", children }: PanelProps) {
  return (
    <section className={`panel ${className}`.trim()}>
      <header className="panel__header">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {action ? <div className="panel__action">{action}</div> : null}
      </header>
      {children}
    </section>
  );
}
