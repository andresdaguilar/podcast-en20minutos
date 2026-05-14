"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { Episode, PodcastId, EpisodesData, PODCAST_CONFIG } from "@/lib/types";
import { EpisodePublishSchedule } from "./EpisodePublishSchedule";
import { DescriptionEditor } from "./DescriptionEditor";
import { AudioGenerator } from "./AudioGenerator";
import { VideoGenerator } from "./VideoGenerator";
import { Save, FileText, BookOpen, Globe } from "lucide-react";

const MarkdownEditor = dynamic(() => import("./MarkdownEditor").then(m => m.MarkdownEditor), {
  ssr: false,
  loading: () => <div className="py-12 text-center text-gray-400">Cargando editor...</div>,
});

interface EpisodeEditorProps {
  podcast: PodcastId;
  number: number;
}

type ContentTab = "script" | "blog" | "blog_en";

const CONTENT_FILES: Record<ContentTab, { file: string; label: string; icon: React.ReactNode }> = {
  script: { file: "Script.md", label: "Script", icon: <FileText size={14} /> },
  blog: { file: "Blog.md", label: "Blog", icon: <BookOpen size={14} /> },
  blog_en: { file: "Blog_en.md", label: "English", icon: <Globe size={14} /> },
};

export function EpisodeEditor({ podcast, number }: EpisodeEditorProps) {
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [activeTab, setActiveTab] = useState<ContentTab>("script");
  const [content, setContent] = useState("");
  const [originalContent, setOriginalContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [fileExists, setFileExists] = useState(false);

  const loadEpisode = useCallback(async () => {
    const res = await fetch("/api/episodes");
    const data: EpisodesData = await res.json();
    const ep = data[podcast]?.find((e) => e.number === number);
    setEpisode(ep || null);
  }, [podcast, number]);

  const loadContent = useCallback(async () => {
    if (!episode) return;
    setLoading(true);
    const file = CONTENT_FILES[activeTab].file;
    const params = new URLSearchParams({ folder: episode.folder, file });
    const res = await fetch(`/api/content?${params}`);
    const json = await res.json();
    setContent(json.content || "");
    setOriginalContent(json.content || "");
    setFileExists(json.exists);
    setLoading(false);
  }, [episode, activeTab]);

  useEffect(() => {
    loadEpisode();
  }, [loadEpisode]);

  useEffect(() => {
    if (episode) loadContent();
  }, [episode, activeTab, loadContent]);

  const handleSave = async () => {
    if (!episode) return;
    setSaving(true);
    const file = CONTENT_FILES[activeTab].file;
    await fetch("/api/content", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder: episode.folder, file, content }),
    });
    setOriginalContent(content);
    setSaving(false);
  };

  const hasChanges = content !== originalContent;

  if (!episode) {
    return <div className="text-gray-500 py-8 text-center">Episodio no encontrado. Escaneá las carpetas primero.</div>;
  }

  return (
    <div className="space-y-6">
      <EpisodePublishSchedule
        podcast={podcast}
        number={number}
        episode={episode}
        onSaved={loadEpisode}
      />

      {/* Content Editor Section */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 px-4 py-3">
          <div className="flex gap-1">
            {(Object.keys(CONTENT_FILES) as ContentTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab
                    ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
                    : "text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
              >
                {CONTENT_FILES[tab].icon}
                {CONTENT_FILES[tab].label}
              </button>
            ))}
          </div>
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save size={14} />
            {saving ? "Guardando..." : "Guardar"}
          </button>
        </div>

        <div className="p-4">
          {loading ? (
            <div className="py-12 text-center text-gray-400">Cargando contenido...</div>
          ) : !fileExists && !content ? (
            <div className="py-12 text-center">
              <p className="text-gray-500 mb-3">
                Este archivo no existe todavía.
              </p>
              <button
                onClick={() => setContent("# ")}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
              >
                Crear {CONTENT_FILES[activeTab].label}
              </button>
            </div>
          ) : (
            <MarkdownEditor
              key={activeTab}
              content={content}
              onChange={setContent}
              showRecordingMode={activeTab === "script"}
              episodeFolder={episode.folder}
              rawMp3Filename={`${PODCAST_CONFIG[podcast].prefix}${number.toString().padStart(3, "0")}-raw.mp3`}
              onRecordingUploaded={loadEpisode}
            />
          )}
        </div>
      </div>

      {/* Descriptions Section */}
      <DescriptionEditor folder={episode.folder} />

      {/* Audio & Video Generation */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <AudioGenerator
          folder={episode.folder}
          podcast={podcast}
          hasEnhanced={episode.audio.enhanced}
          hasComplete={episode.audio.complete}
        />
        <VideoGenerator
          folder={episode.folder}
          podcast={podcast}
          hasComplete={episode.audio.complete}
          hasYoutubeCover={episode.images.youtube}
          hasVideo={episode.hasVideo}
        />
      </div>
    </div>
  );
}
