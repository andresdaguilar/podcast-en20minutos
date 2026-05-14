import { PodcastId, PODCAST_CONFIG } from "./types";
import type { EpisodeDisplayKind } from "./episodeStatus";

/** Agregados a los estados derivados por episodio (ver {@link deriveEpisodeDisplayStatus}). */
export type EpisodeStatusFilter = "unpublished" | "all" | EpisodeDisplayKind;

export const DEFAULT_STATUS_FILTER: EpisodeStatusFilter = "unpublished";

const PODCAST_IDS = Object.keys(PODCAST_CONFIG) as PodcastId[];

const DISPLAY_KINDS: readonly EpisodeDisplayKind[] = [
  "published",
  "scheduled",
  "no_script",
  "missing_audio",
  "ready",
];

export function parsePodcastSearchParam(value: string | null): PodcastId {
  if (value && PODCAST_IDS.includes(value as PodcastId)) {
    return value as PodcastId;
  }
  return "historia";
}

export function parseStatusSearchParam(value: string | null): EpisodeStatusFilter {
  if (value === "all") return "all";
  if (value === "unpublished") return "unpublished";
  if (value && DISPLAY_KINDS.includes(value as EpisodeDisplayKind)) {
    return value as EpisodeDisplayKind;
  }
  return DEFAULT_STATUS_FILTER;
}

/** Path con query para el dashboard principal (/, /?podcast=…, etc.). */
export function buildDashboardHref(
  podcast: PodcastId,
  status: EpisodeStatusFilter = DEFAULT_STATUS_FILTER
): string {
  const p = new URLSearchParams();
  if (podcast !== "historia") p.set("podcast", podcast);
  if (status !== DEFAULT_STATUS_FILTER) p.set("status", status);
  const q = p.toString();
  return q ? `/?${q}` : "/";
}
