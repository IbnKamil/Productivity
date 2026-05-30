import { AuthGate } from "@/components/AuthGate";
import { TunnelTaskCard } from "@/features/current-task/TunnelTaskCard";

export default function HomePage() {
  return (
    <AuthGate>
      <main className="mx-auto grid max-w-4xl px-6 py-10">
        <TunnelTaskCard />
        <p className="mx-auto mt-6 max-w-xl text-center text-sm text-slate-400">
          Future tasks stay hidden. Finish the visible action to keep momentum without overload.
        </p>
      </main>
    </AuthGate>
  );
}
