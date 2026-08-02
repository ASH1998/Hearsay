import { GameShell } from "@/components/game-shell";
import { ReplayExperience } from "@/components/replay-experience";

export default function Home() {
  return process.env.NEXT_PUBLIC_HEARSAY_REPLAY_HOME === "1" ? (
    <ReplayExperience />
  ) : (
    <GameShell />
  );
}
