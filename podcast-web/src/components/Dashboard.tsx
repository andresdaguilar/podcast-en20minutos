"use client";

import { useMemo } from "react";
import { EpisodesData, PodcastId, PODCAST_CONFIG } from "@/lib/types";
import type { EpisodeStatusFilter } from "@/lib/dashboardUrl";
import { EpisodeTable } from "./EpisodeTable";
import {
  deriveEpisodeDisplayStatus,
  EPISODE_STATUS_LABELS,
} from "@/lib/episodeStatus";
import { Filter } from "lucide-react";

interface DashboardProps {
  data: EpisodesData;
  activePodcast: PodcastId;
  onChangePodcast: (id: PodcastId) => void;
  statusFilter: EpisodeStatusFilter;
  onChangeStatusFilter: (filter: EpisodeStatusFilter) => void;
}

const podcastIds: PodcastId[] = ["historia", "filosofia", "libros", "mitologia"];

const FILTER_ORDER: EpisodeStatusFilter[] = [
  "unpublished",
  "all",
  "no_script",
  "missing_audio",
  "ready",
  "scheduled",
  "published",
];

const FILTER_LABELS: Record<EpisodeStatusFilter, string> = {
  unpublished: "Sin Publicar",
  all: "Todos",
  ...EPISODE_STATUS_LABELS,
};

export function Dashboard({
  data,
  activePodcast,
  onChangePodcast,
  statusFilter,
  onChangeStatusFilter,
}: DashboardProps) {
  const allEpisodes = data[activePodcast];

  const statusCounts = useMemo(() => {
    const counts: Record<EpisodeStatusFilter, number> = {
      unpublished: 0,
      all: allEpisodes.length,
      published: 0,
      scheduled: 0,
      no_script: 0,
      missing_audio: 0,
      ready: 0,
    };
    for (const ep of allEpisodes) {
      if (!ep.published) counts.unpublished += 1;
      const kind = deriveEpisodeDisplayStatus(ep).kind;
      counts[kind] += 1;
    }
    return counts;
  }, [allEpisodes]);

  const filteredEpisodes = useMemo(() => {
    if (statusFilter === "all") return allEpisodes;
    if (statusFilter === "unpublished") {
      return allEpisodes.filter((ep) => !ep.published);
    }
    return allEpisodes.filter(
      (ep) => deriveEpisodeDisplayStatus(ep).kind === statusFilter
    );
  }, [allEpisodes, statusFilter]);

  return (
    <div>
      <div className="flex gap-1 mb-4 bg-white dark:bg-gray-900 p-1 rounded-xl border border-gray-200 dark:border-gray-800">
        {podcastIds.map((id) => (
          <button
            key={id}
            type="button"
            onClick={() => onChangePodcast(id)}
            className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activePodcast === id
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
          >
            {PODCAST_CONFIG[id].label}
            <span className="ml-2 text-xs opacity-75">
              ({data[id].length})
            </span>
          </button>
        ))}
      </div>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div className="flex items-center gap-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          <Filter size={14} className="shrink-0" />
          Estado
        </div>
        <div className="flex flex-wrap gap-1.5">
          {FILTER_ORDER.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => onChangeStatusFilter(key)}
              className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${
                statusFilter === key
                  ? "bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              {FILTER_LABELS[key]}
              <span
                className={
                  statusFilter === key
                    ? "opacity-80"
                    : "text-gray-500 dark:text-gray-500"
                }
              >
                ({statusCounts[key]})
              </span>
            </button>
          ))}
        </div>
      </div>

      {statusFilter !== "all" && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Mostrando {filteredEpisodes.length} de {allEpisodes.length} episodios
        </p>
      )}

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <EpisodeTable
          episodes={filteredEpisodes}
          podcast={activePodcast}
        />
      </div>
    </div>
  );
}
