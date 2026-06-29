interface PlaceholderCardProps {
  title: string;
  description?: string;
  className?: string;
  children?: React.ReactNode;
}

export function PlaceholderCard({
  title,
  description,
  className = "",
  children,
}: PlaceholderCardProps) {
  return (
    <div
      className={`border-border bg-surface hover:border-border-subtle hover:bg-surface-elevated rounded-xl border p-5 transition-colors ${className}`}
    >
      <h3 className="text-foreground text-sm font-semibold">{title}</h3>
      {description && <p className="text-muted mt-1 text-xs">{description}</p>}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
