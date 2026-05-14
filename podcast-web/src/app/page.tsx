"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Dashboard } from "@/components/Dashboard";
import { EpisodesData, PodcastId } from "@/lib/types";
import {
  parsePodcastSearchParam,
  parseStatusSearchParam,
  buildDashboardHref,
  type EpisodeStatusFilter,
} from "@/lib/dashboardUrl";

function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const activePodcast = useMemo(
    () => parsePodcastSearchParam(searchParams.get("podcast")),
    [searchParams]
  );
  const statusFilter = useMemo(
    () => parseStatusSearchParam(searchParams.get("status")),
    [searchParams]
  );

  const [data, setData] = useState<EpisodesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const fetchData = async () => {
    const res = await fetch("/api/episodes");
    const json = await res.json();
    if (json.filosofia) {
      setData(json);
    }
    setLoading(false);
  };

  const handleScan = async () => {
    setScanning(true);
    const res = await fetch("/api/scan", { method: "POST" });
    const json = await res.json();
    if (json.success) {
      setData(json.data);
    }
    setScanning(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const navigateDashboard = (path: string) =>
    router.replace(path, { scroll: false });

  const handleChangePodcast = (id: PodcastId) => {
    navigateDashboard(buildDashboardHref(id, statusFilter));
  };

  const handleChangeStatusFilter = (filter: EpisodeStatusFilter) => {
    navigateDashboard(buildDashboardHref(activePodcast, filter));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            Podcast en 20 Minutos
          </h1>
          <button
            type="button"
            onClick={handleScan}
            disabled={scanning}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {scanning ? "Escaneando..." : "Escanear carpetas"}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Cargando...</div>
        ) : !data ||
          Object.values(data).every((eps) => eps.length === 0) ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">
              No hay episodios cargados. Escaneá las carpetas para detectar el
              contenido existente.
            </p>
            <button
              type="button"
              onClick={handleScan}
              disabled={scanning}
              className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {scanning ? "Escaneando..." : "Escanear carpetas"}
            </button>
          </div>
        ) : (
          <Dashboard
            data={data}
            activePodcast={activePodcast}
            onChangePodcast={handleChangePodcast}
            statusFilter={statusFilter}
            onChangeStatusFilter={handleChangeStatusFilter}
          />
        )}
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center text-gray-500">
          Cargando…
        </div>
      }
    >
      <HomeContent />
    </Suspense>
  );
}
