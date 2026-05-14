import { Episode, EpisodesData, PodcastId, PODCAST_CONFIG } from "./types";

const PODCAST_IDS = Object.keys(PODCAST_CONFIG) as PodcastId[];

export type EpisodeDisplayKind =
  | "published"
  | "scheduled"
  | "no_script"
  | "missing_audio"
  | "ready";

export interface EpisodeDisplayStatus {
  kind: EpisodeDisplayKind;
  /** YYYY-MM-DD cuando aplica */
  date?: string | null;
}

/** Fecha calendario en UTC YYYY-MM-DD (comparaciones lexicográficas son válidas). */
export function utcDateISO(d: Date = new Date()): string {
  return d.toISOString().slice(0, 10);
}

/**
 * Promueve a publicados los episodios con fecha programada cumplida o vencida.
 * Mutativo. Devuelve si hubo cambios (para persistir).
 */
export function applyDueScheduledPublishing(data: EpisodesData): boolean {
  const today = utcDateISO();
  let changed = false;
  for (const pid of PODCAST_IDS) {
    for (const ep of data[pid]) {
      if (!ep.published && ep.publishDate && ep.publishDate <= today) {
        ep.published = true;
        changed = true;
      }
    }
  }
  return changed;
}

/**
 * Debe llamarse después de {@link applyDueScheduledPublishing} con los mismos datos
 * para que Estados y archivo JSON coincidan.
 */
export function deriveEpisodeDisplayStatus(ep: Episode): EpisodeDisplayStatus {
  const today = utcDateISO();

  if (ep.published) {
    return { kind: "published", date: ep.publishDate };
  }

  if (ep.publishDate && ep.publishDate > today) {
    return { kind: "scheduled", date: ep.publishDate };
  }

  if (!ep.content.script) {
    return { kind: "no_script" };
  }

  const hasAudio =
    ep.audio.raw || ep.audio.enhanced || ep.audio.complete;
  if (!hasAudio) {
    return { kind: "missing_audio" };
  }

  return { kind: "ready" };
}

export const EPISODE_STATUS_LABELS: Record<EpisodeDisplayKind, string> = {
  published: "Publicado",
  scheduled: "Programado",
  no_script: "Sin guión",
  missing_audio: "Falta audio",
  ready: "Guión y audio listos",
};

export function episodeStatusBadgeClass(kind: EpisodeDisplayKind): string {
  switch (kind) {
    case "published":
      return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
    case "scheduled":
      return "bg-sky-100 text-sky-800 dark:bg-sky-900/35 dark:text-sky-400";
    case "ready":
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400";
    case "missing_audio":
      return "bg-amber-100 text-amber-900 dark:bg-amber-900/35 dark:text-amber-400";
    case "no_script":
    default:
      return "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
  }
}

export function formatPublishDateLabel(iso?: string | null): string {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat("es", { dateStyle: "medium", timeZone: "UTC" }).format(
      new Date(`${iso}T12:00:00.000Z`)
    );
  } catch {
    return iso;
  }
}
