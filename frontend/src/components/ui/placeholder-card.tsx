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
      className={`rounded-xl border border-border bg-surface p-5 transition-colors hover:border-border-subtle hover:bg-surface-elevated ${className}`}
    >
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 text-xs text-muted">{description}</p>
      )}
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
