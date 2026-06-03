import { Icon } from "@/components/stitch/Icon";

export function LoadingState({
  label,
  compact,
}: {
  label: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 text-center ${
        compact ? "px-4 py-8" : "px-6 py-16"
      }`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <Icon name="progress_activity" className="animate-spin text-4xl text-primary-container" />
      <p className="max-w-xs font-body-md text-body-md text-on-surface-variant">{label}</p>
    </div>
  );
}

export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-2 px-1" aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="h-16 rounded-lg bg-surface-container-high"
          style={{ opacity: 1 - i * 0.15 }}
        />
      ))}
    </div>
  );
}
