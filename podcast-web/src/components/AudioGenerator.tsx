"use client";

import { useState } from "react";
import { PodcastId } from "@/lib/types";
import { Music, Play, Check, AlertCircle, Loader } from "lucide-react";

interface AudioGeneratorProps {
  folder: string;
  podcast: PodcastId;
  hasEnhanced: boolean;
  hasComplete: boolean;
}

export function AudioGenerator({
  folder,
  podcast,
  hasEnhanced,
  hasComplete,
}: AudioGeneratorProps) {
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const canGenerate = hasEnhanced && !generating;

  const handleGenerate = async () => {
    setGenerating(true);
    setResult(null);
    try {
      const res = await fetch("/api/audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder, podcast }),
      });
      const json = await res.json();
      if (json.success) {
        setResult({ success: true, message: "Audio generado correctamente" });
      } else {
        setResult({ success: false, message: json.error || "Error desconocido" });
      }
    } catch (err) {
      setResult({ success: false, message: "Error de conexión" });
    }
    setGenerating(false);
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Music size={18} className="text-indigo-500" />
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">
          Audio Completo
        </h3>
      </div>

      <div className="space-y-2 text-sm text-gray-500 mb-4">
        <div className="flex items-center gap-2">
          {hasEnhanced ? (
            <Check size={14} className="text-green-500" />
          ) : (
            <AlertCircle size={14} className="text-yellow-500" />
          )}
          <span>Audio enhanced</span>
        </div>
        <div className="flex items-center gap-2">
          {hasComplete ? (
            <Check size={14} className="text-green-500" />
          ) : (
            <span className="w-3.5 h-3.5 rounded-full border-2 border-gray-300 dark:border-gray-600" />
          )}
          <span>Audio completo (intro + enhanced + outro)</span>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={!canGenerate}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {generating ? (
          <>
            <Loader size={14} className="animate-spin" />
            Generando...
          </>
        ) : (
          <>
            <Play size={14} />
            Generar audio completo
          </>
        )}
      </button>

      {!hasEnhanced && (
        <p className="mt-2 text-xs text-yellow-600 dark:text-yellow-400">
          Se necesita el audio enhanced para generar el completo
        </p>
      )}

      {result && (
        <div
          className={`mt-3 p-2 rounded-lg text-xs ${
            result.success
              ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
              : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
          }`}
        >
          {result.message}
        </div>
      )}
    </div>
  );
}
