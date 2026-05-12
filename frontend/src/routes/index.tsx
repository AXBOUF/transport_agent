import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense, useEffect, useState } from "react";

export const Route = createFileRoute("/")({
  component: Index,
  head: () => ({
    meta: [
      { title: "Live Map — Interactive Navigation" },
      { name: "description", content: "Real-time interactive map with custom themes and live location tracking." },
    ],
  }),
});

const LiveMap = lazy(() => import("@/components/LiveMap"));

function Index() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="text-sm text-muted-foreground">Loading map…</div>
      </div>
    );
  }
  return (
    <Suspense fallback={<div className="flex h-screen w-full items-center justify-center bg-background"><div className="text-sm text-muted-foreground">Loading map…</div></div>}>
      <LiveMap />
    </Suspense>
  );
}
