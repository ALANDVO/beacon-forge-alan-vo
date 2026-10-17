import "./Loading.css";

export default function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="loading-state" data-testid="loading">
      <div className="spinner" />
      <span className="loading-label">{label}</span>
    </div>
  );
}