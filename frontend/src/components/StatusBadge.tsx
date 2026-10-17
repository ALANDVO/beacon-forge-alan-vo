interface Props {
  status: string;
  size?: "sm" | "md";
}

const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  paused: "Paused",
  archived: "Archived",
  completed: "Completed",
  pending: "Pending",
  running: "Running",
  failed: "Failed",
};

export default function StatusBadge({ status, size = "md" }: Props) {
  const label = STATUS_LABELS[status] ?? status;
  const sizeClass = size === "sm" ? "status-badge-sm" : "";
  return (
    <span className={`status-badge status-${status} ${sizeClass}`} data-testid="status-badge">
      {label}
    </span>
  );
}