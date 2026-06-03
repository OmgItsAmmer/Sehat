export function Icon({
  name,
  filled,
  className = "",
}: {
  name: string;
  filled?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`material-symbols-outlined ${filled ? "material-symbols-filled" : ""} ${className}`}
    >
      {name}
    </span>
  );
}
