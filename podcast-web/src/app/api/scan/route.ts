import { NextResponse } from "next/server";
import {
  scanAll,
  loadEpisodes,
  mergeScannedWithExisting,
  saveEpisodes,
} from "@/lib/scanner";
import { applyDueScheduledPublishing } from "@/lib/episodeStatus";

export async function POST() {
  try {
    const scanned = scanAll();
    const existing = loadEpisodes();
    const merged = mergeScannedWithExisting(scanned, existing);
    applyDueScheduledPublishing(merged);
    saveEpisodes(merged);
    return NextResponse.json({ success: true, data: merged });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
