"use client";

import Link from "next/link";
import { Episode, PodcastId } from "@/lib/types";
import {
  deriveEpisodeDisplayStatus,
  EPISODE_STATUS_LABELS,
  episodeStatusBadgeClass,
  formatPublishDateLabel,
} from "@/lib/episodeStatus";
import {
  FileText,
  Image,
  Music,
  Video,
  Check,
  X,
  Globe,
  MessageSquare,
} from "lucide-react";

interface EpisodeTableProps {
  episodes: Episode[];
  podcast: PodcastId;
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${
        active ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
      }`}
    />
  );
}

function EpisodePublicationCell({ ep }: { ep: Episode }) {
  const st = deriveEpisodeDisplayStatus(ep);
  return (
    <div className="flex flex-col items-center gap-0.5 max-w-[9rem] mx-auto">
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${episodeStatusBadgeClass(
          st.kind
        )}`}
      >
        {EPISODE_STATUS_LABELS[st.kind]}
      </span>
      {(st.kind === "scheduled" || st.kind === "published") && st.date && (
        <span className="text-[11px] leading-tight text-gray-500 dark:text-gray-400">
          {formatPublishDateLabel(st.date)}
        </span>
      )}
    </div>
  );
}

function Badge({
  label,
  active,
}: {
  label: string;
  active: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
        active
          ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
          : "bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-600"
      }`}
    >
      {label}
    </span>
  );
}

export function EpisodeTable({ episodes, podcast }: EpisodeTableProps) {
  if (episodes.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        No hay episodios para este podcast
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
            <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              #
            </th>
            <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              Título
            </th>
            <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              <FileText size={14} className="inline" />
            </th>
            <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              <Globe size={14} className="inline" />
            </th>
            <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              <MessageSquare size={14} className="inline" />
            </th>
            <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              <Image size={14} className="inline" />
            </th>
            <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              <Music size={14} className="inline" />
            </th>
            <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              <Video size={14} className="inline" />
            </th>
            <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-gray-400">
              Estado
            </th>
          </tr>
        </thead>
        <tbody>
          {episodes.map((ep) => (
            <tr
              key={ep.number}
              className="border-b border-gray-100 dark:border-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
            >
              <td className="px-4 py-3 font-mono text-gray-500">
                {String(ep.number).padStart(3, "0")}
              </td>
              <td className="px-4 py-3">
                <Link
                  href={`/episode?podcast=${podcast}&number=${ep.number}`}
                  className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium"
                >
                  {ep.title || `Episodio ${ep.number}`}
                </Link>
              </td>
              <td className="px-4 py-3 text-center">
                <div className="flex gap-1 justify-center">
                  <Badge label="S" active={ep.content.script} />
                  <Badge label="B" active={ep.content.blog} />
                </div>
              </td>
              <td className="px-4 py-3 text-center">
                {ep.content.translations.length > 0 ? (
                  <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                    {ep.content.translations.join(", ").toUpperCase()}
                  </span>
                ) : (
                  <X size={14} className="inline text-gray-300 dark:text-gray-600" />
                )}
              </td>
              <td className="px-4 py-3 text-center">
                {ep.hasDescriptions ? (
                  <Check size={14} className="inline text-green-500" />
                ) : (
                  <X size={14} className="inline text-gray-300 dark:text-gray-600" />
                )}
              </td>
              <td className="px-4 py-3 text-center">
                <div className="flex gap-1 justify-center">
                  <Badge label="B" active={ep.images.blog} />
                  <Badge label="S" active={ep.images.spotify} />
                  <Badge label="Y" active={ep.images.youtube} />
                </div>
              </td>
              <td className="px-4 py-3 text-center">
                <div className="flex gap-1 justify-center">
                  <Badge label="R" active={ep.audio.raw} />
                  <Badge label="E" active={ep.audio.enhanced} />
                  <Badge label="C" active={ep.audio.complete} />
                </div>
              </td>
              <td className="px-4 py-3 text-center">
                <StatusDot active={ep.hasVideo} />
              </td>
              <td className="px-4 py-3 text-center">
                <EpisodePublicationCell ep={ep} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
