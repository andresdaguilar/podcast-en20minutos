"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { EpisodeEditor } from "@/components/EpisodeEditor";
import { PodcastId, PODCAST_CONFIG, EpisodesData } from "@/lib/types";
import { buildDashboardHref } from "@/lib/dashboardUrl";
import { ArrowLeft } from "lucide-react";

function EpisodePageContent() {
  const searchParams = useSearchParams();
  const podcast = searchParams.get("podcast") as PodcastId;
  const number = parseInt(searchParams.get("number") || "0", 10);
  const [title, setTitle] = useState("");

  useEffect(() => {
    if (!podcast || !number) return;
    fetch("/api/episodes")
      .then((res) => res.json())
      .then((data: EpisodesData) => {
        const ep = data[podcast]?.find((e) => e.number === number);
        if (ep?.title) setTitle(ep.title);
      });
  }, [podcast, number]);

  if (!podcast || !number) {
    return (
      <div className="p-8 text-center text-gray-500">
        Parámetros inválidos
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <Link
            href={buildDashboardHref(podcast)}
            className="text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <span className="text-sm text-gray-500">
              {PODCAST_CONFIG[podcast].label} · Episodio {number}
            </span>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">
              {title || `Episodio ${number}`}
            </h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        <EpisodeEditor podcast={podcast} number={number} />
      </main>
    </div>
  );
}

export default function EpisodePage() {
  return (
    <Suspense fallback={<div className="p-8 text-center">Cargando...</div>}>
      <EpisodePageContent />
    </Suspense>
  );
}
