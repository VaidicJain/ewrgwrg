"use client";

import { CalendarDays, RotateCcw } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  CONFIDENCE_OPTIONS,
  CUTOFF_OPTIONS,
  DATA_END,
  DATA_START,
  DATE_PRESETS,
  DEFAULT_FILTERS,
} from "@/lib/config";
import type { Filters } from "@/lib/types";
import { cn } from "@/lib/utils";

interface FiltersBarProps {
  initial: Filters;
  isLoading: boolean;
  onApply: (filters: Filters) => void;
}

/** Returns a message when the draft cannot be applied, otherwise null. */
function validate(draft: Filters): string | null {
  if (!draft.startDate || !draft.endDate) return "Choose a start and end date.";
  if (draft.endDate < draft.startDate) return "The end date must be on or after the start date.";
  if (draft.startDate < DATA_START || draft.endDate > DATA_END) {
    return "Data is available for 1-31 January 2026.";
  }
  return null;
}

export function FiltersBar({ initial, isLoading, onApply }: FiltersBarProps) {
  const [draft, setDraft] = useState<Filters>(initial);
  const ids = { start: useId(), end: useId(), cutoff: useId(), compare: useId(), confidence: useId() };

  const problem = validate(draft);
  const update = <K extends keyof Filters>(key: K, value: Filters[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  const applyPreset = (startDate: string, endDate: string) => {
    const next = { ...draft, startDate, endDate };
    setDraft(next);
    onApply(next);
  };

  const reset = () => {
    setDraft(DEFAULT_FILTERS);
    onApply(DEFAULT_FILTERS);
  };

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <CalendarDays className="size-4 text-muted-foreground" aria-hidden />
          <span className="mr-1 text-sm font-medium">Delivery period</span>
          {DATE_PRESETS.map((preset) => {
            const active = draft.startDate === preset.startDate && draft.endDate === preset.endDate;
            return (
              <button
                key={preset.id}
                type="button"
                onClick={() => applyPreset(preset.startDate, preset.endDate)}
                aria-pressed={active}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "border-primary bg-primary text-primary-foreground"
                    : "bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                {preset.label}
              </button>
            );
          })}
        </div>

        <form
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6 lg:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            if (!problem) onApply(draft);
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor={ids.start}>From</Label>
            <Input
              id={ids.start}
              type="date"
              min={DATA_START}
              max={DATA_END}
              value={draft.startDate}
              onChange={(event) => update("startDate", event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={ids.end}>To</Label>
            <Input
              id={ids.end}
              type="date"
              min={DATA_START}
              max={DATA_END}
              value={draft.endDate}
              onChange={(event) => update("endDate", event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={ids.cutoff}>Decision cutoff (day before, UTC)</Label>
            <Select
              id={ids.cutoff}
              value={draft.cutoffTime}
              onChange={(event) => update("cutoffTime", event.target.value)}
            >
              {CUTOFF_OPTIONS.map((time) => (
                <option key={time} value={time}>
                  {time}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={ids.compare}>Compare with cutoff</Label>
            <Select
              id={ids.compare}
              value={draft.compareCutoffTime}
              onChange={(event) => update("compareCutoffTime", event.target.value)}
            >
              {CUTOFF_OPTIONS.map((time) => (
                <option key={time} value={time}>
                  {time}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={ids.confidence}>Safety confidence</Label>
            <Select
              id={ids.confidence}
              value={String(draft.confidence)}
              onChange={(event) => update("confidence", Number(event.target.value))}
            >
              {CONFIDENCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={Boolean(problem) || isLoading} className="flex-1">
              {isLoading ? "Updating..." : "Apply"}
            </Button>
            <Button type="button" variant="outline" onClick={reset} aria-label="Reset filters">
              <RotateCcw />
            </Button>
          </div>
        </form>

        {problem && (
          <p role="status" className="text-sm text-destructive">
            {problem}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
