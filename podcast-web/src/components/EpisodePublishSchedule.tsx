"use client";

import { useEffect, useState } from "react";
import { Episode, PodcastId } from "@/lib/types";
import {
  deriveEpisodeDisplayStatus,
  EPISODE_STATUS_LABELS,
  episodeStatusBadgeClass,
  formatPublishDateLabel,
} from "@/lib/episodeStatus";

async function patchEpisode(
  podcast: PodcastId,
  number: number,
  updates: { publishDate?: string | null; published?: boolean }
) {
  const res = await fetch("/api/episodes", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ podcast, number, updates }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || "Error al guardar");
  return json.episode as Episode;
}

interface EpisodePublishScheduleProps {
  episode: Episode;
  podcast: PodcastId;
  number: number;
  onSaved: () => void;
}

export function EpisodePublishSchedule({
  episode,
  podcast,
  number,
  onSaved,
}: EpisodePublishScheduleProps) {
  const [dateInput, setDateInput] = useState(episode.publishDate ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDateInput(episode.publishDate ?? "");
  }, [episode.folder, episode.publishDate]);

  const status = deriveEpisodeDisplayStatus(episode);

  const wrap = async (fn: () => void | Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Publicación</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xl">
            Programá una fecha (se publicará solo ese día según UTC) o marcá como publicado en
            cualquier momento. Los cambios aquí modifican&nbsp;
            <code className="text-[11px] bg-gray-100 dark:bg-gray-800 px-1 rounded">data/episodes.json</code>.
          </p>
        </div>
        <span
          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${episodeStatusBadgeClass(
            status.kind
          )}`}
        >
          {EPISODE_STATUS_LABELS[status.kind]}
        </span>
      </div>

      {(status.kind === "published" || status.kind === "scheduled") && status.date && (
        <p className="text-sm text-gray-700 dark:text-gray-300">
          Fecha: <span className="font-medium">{formatPublishDateLabel(status.date)}</span>
        </p>
      )}

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {!episode.published && (
        <div className="flex flex-col sm:flex-row sm:flex-wrap gap-3 sm:items-end">
          <div className="flex flex-col gap-1">
            <label htmlFor="publish-date" className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Fecha de publicación
            </label>
            <input
              id="publish-date"
              type="date"
              value={dateInput}
              onChange={(e) => setDateInput(e.target.value)}
              className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2 text-sm text-gray-900 dark:text-white"
            />
          </div>
          <button
            type="button"
            disabled={busy || !dateInput}
            onClick={() =>
              wrap(() => patchEpisode(podcast, number, { publishDate: dateInput }))
            }
            className="px-4 py-2 rounded-lg text-sm font-medium bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Guardar programación
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => wrap(() => patchEpisode(podcast, number, { published: true }))}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
          >
            Marcar publicado ahora
          </button>
          {episode.publishDate && (
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                wrap(() =>
                  patchEpisode(podcast, number, { publishDate: null })
                )
              }
              className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              Quitar programación
            </button>
          )}
        </div>
      )}

      {episode.published && (
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Episodio marcado como publicado. La tabla principal mostrará el estado con la fecha asignada.
        </p>
      )}
    </div>
  );
}
