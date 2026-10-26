import { Wind } from "lucide-react";

import { Badge } from "@/components/ui/badge";

export function AppHeader() {
  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Wind className="size-5" aria-hidden />
          </div>
          <div>
            <h1 className="text-lg font-semibold leading-tight tracking-tight">Wind Forecast Monitor</h1>
            <p className="text-sm text-muted-foreground">
              Day-ahead decision support for UK power buyers
            </p>
          </div>
        </div>
        <div className="hidden items-center gap-2 sm:flex">
          <Badge variant="secondary">Elexon BMRS</Badge>
          <Badge variant="outline">GB national wind</Badge>
        </div>
      </div>
    </header>
  );
}
