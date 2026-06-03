/** Reference page — tokens from Stitch Design System asset */
export function DesignSystem() {
  const colors = [
    ["primary", "#005454"],
    ["primary-container", "#0d6e6e"],
    ["secondary", "#bb0112"],
    ["secondary-container", "#e02928"],
    ["error", "#ba1a1a"],
    ["background", "#f8f9ff"],
    ["surface-container", "#e5eeff"],
    ["on-surface", "#0b1c30"],
  ] as const;

  return (
    <div className="min-h-dvh bg-background p-container-padding font-body-md text-on-background">
      <h1 className="font-headline-lg text-headline-lg text-primary">Sehat Design System</h1>
      <p className="mt-2 font-body-md text-on-surface-variant">
        Exported from Stitch project 14292060559091575997. Screens in{" "}
        <code className="rounded bg-surface-container px-1">frontend/stitch-raw/</code>.
      </p>

      <section className="mt-8">
        <h2 className="font-headline-md text-headline-md">Color roles</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {colors.map(([name, hex]) => (
            <div
              key={name}
              className="overflow-hidden rounded-xl border border-outline-variant bg-surface"
            >
              <div className="h-16" style={{ backgroundColor: hex }} />
              <div className="p-3">
                <p className="font-label-md text-label-md">{name}</p>
                <p className="font-mono-clinical text-mono-clinical text-on-surface-variant">{hex}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="font-headline-md text-headline-md">Typography</h2>
        <div className="mt-4 space-y-3 rounded-xl border border-outline-variant bg-surface p-6">
          <p className="font-display-lg text-display-lg text-on-surface">Display LG</p>
          <p className="font-headline-lg text-headline-lg text-on-surface">Headline LG</p>
          <p className="font-headline-md text-headline-md text-on-surface">Headline MD</p>
          <p className="font-title-lg text-title-lg text-on-surface">Title LG</p>
          <p className="font-body-lg text-body-lg text-on-surface">Body LG — clinical copy</p>
          <p className="font-body-md text-body-md text-on-surface-variant">Body MD — secondary</p>
          <p className="font-label-md text-label-md text-primary">Label MD — actions</p>
          <p className="font-mono-clinical text-mono-clinical text-on-surface-variant">
            MONO CLINICAL — 02:14 PM
          </p>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="font-headline-md text-headline-md">Screen references</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {["clinic-dashboard", "analytics", "slack-card"].map((name) => (
            <figure
              key={name}
              className="overflow-hidden rounded-xl border border-outline-variant bg-surface"
            >
              <img
                src={`/stitch/${name}.png`}
                alt={name}
                className="w-full border-b border-outline-variant"
              />
              <figcaption className="p-2 font-label-md text-label-md capitalize">
                {name.replace(/-/g, " ")}
              </figcaption>
            </figure>
          ))}
        </div>
      </section>
    </div>
  );
}
