import React from 'react';

export const PageHeader: React.FC<{ eyebrow: string; title: string; children?: React.ReactNode }> = ({
  eyebrow,
  title,
  children,
}) => (
  <header className="pb-8 border-b border-rule">
    <p className="text-xs font-medium text-muted uppercase tracking-[0.12em]">{eyebrow}</p>
    <h1 className="mt-3 font-serif text-[2.25rem] sm:text-[2.75rem] leading-[1.1] tracking-[-0.01em] text-ink max-w-3xl">
      {title}
    </h1>
    {children && <div className="mt-4 text-[15px] leading-relaxed text-ink-2 max-w-2xl">{children}</div>}
  </header>
);

export const Section: React.FC<{
  title: string;
  description?: React.ReactNode;
  aside?: React.ReactNode;
  children: React.ReactNode;
}> = ({ title, description, aside, children }) => (
  <section className="py-10 border-b border-rule last:border-b-0">
    <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted max-w-2xl">{description}</p>}
      </div>
      {aside}
    </div>
    {children}
  </section>
);

export const Stat: React.FC<{ value: string; label: string; note?: string }> = ({ value, label, note }) => (
  <div className="py-5 sm:px-6 first:sm:pl-0">
    <div className="font-serif text-[2.25rem] leading-none tracking-tight text-ink tabular">{value}</div>
    <div className="mt-2 text-sm text-ink-2">{label}</div>
    {note && <div className="mt-0.5 text-xs text-muted">{note}</div>}
  </div>
);

export const StatRow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="grid grid-cols-2 lg:grid-cols-4 divide-rule lg:divide-x border-b border-rule">{children}</div>
);

export const Code: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="font-mono text-[0.85em] px-1 py-px rounded bg-sunken text-ink-2">{children}</code>
);
