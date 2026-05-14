"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  Circle,
  Download,
  Loader,
  Mic,
  Pause,
  Play,
  Square,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { isChromeDesktop } from "@/lib/chromeDesktop";
import { useBrowserRecorder } from "@/hooks/useBrowserRecorder";

function formatElapsed(totalSec: number): string {
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function RecordingLevelMeter({ stream }: { stream: MediaStream | null }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (!stream) {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      void ctxRef.current?.close().catch(() => undefined);
      ctxRef.current = null;
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx2d = canvas.getContext("2d");
    if (!ctx2d) return;

    const audioCtx = new AudioContext();
    ctxRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);

    const draw = () => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i]! - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / data.length);
      const level = Math.min(1, rms * 4);

      const w = canvas.width;
      const h = canvas.height;
      ctx2d.clearRect(0, 0, w, h);
      ctx2d.fillStyle = "#e5e7eb";
      ctx2d.fillRect(0, 0, w, h);
      ctx2d.fillStyle = "#10b981";
      ctx2d.fillRect(0, 0, w * level, h);

      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      source.disconnect();
      analyser.disconnect();
      void audioCtx.close().catch(() => undefined);
      if (ctxRef.current === audioCtx) ctxRef.current = null;
    };
  }, [stream]);

  return (
    <canvas
      ref={canvasRef}
      width={120}
      height={10}
      className="rounded border border-gray-200"
      aria-label="Nivel de audio"
    />
  );
}

interface RecordingModeOverlayProps {
  scriptHtml: string;
  episodeFolder: string;
  rawMp3Filename: string;
  onClose: () => void;
  onUploaded: () => void;
}

export function RecordingModeOverlay({
  scriptHtml,
  episodeFolder,
  rawMp3Filename,
  onClose,
  onUploaded,
}: RecordingModeOverlayProps) {
  const supported = isChromeDesktop();
  const {
    status,
    error,
    finalBlob,
    elapsedSec,
    meterStream,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    discardSession,
    resetAfterSuccess,
    hasPendingBlob,
    isActive,
  } = useBrowserRecorder();
  const [tabHidden, setTabHidden] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const beginRecording = useCallback(() => {
    setUploadMessage(null);
    void startRecording();
  }, [startRecording]);

  useEffect(() => {
    const onVis = () => setTabHidden(document.visibilityState === "hidden");
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isActive || hasPendingBlob) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isActive, hasPendingBlob]);

  const tryClose = useCallback(() => {
    if (isActive) {
      if (
        !confirm(
          "Hay una grabación en curso. Si salís se descarta. ¿Continuar?"
        )
      ) {
        return;
      }
      discardSession();
      onClose();
      return;
    }
    if (hasPendingBlob) {
      if (
        !confirm(
          "Hay una grabación lista sin guardar en el servidor. ¿Salir sin guardar?"
        )
      ) {
        return;
      }
      discardSession();
    }
    onClose();
  }, [onClose, discardSession, isActive, hasPendingBlob]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        tryClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tryClose]);

  const downloadWebm = useCallback(() => {
    if (!finalBlob) return;
    const url = URL.createObjectURL(finalBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "grabacion.webm";
    a.click();
    URL.revokeObjectURL(url);
  }, [finalBlob]);

  const uploadMp3 = useCallback(async () => {
    if (!finalBlob) return;
    setUploading(true);
    setUploadMessage(null);
    try {
      const fd = new FormData();
      fd.append("folder", episodeFolder);
      fd.append("filename", rawMp3Filename);
      fd.append("file", finalBlob, "recording.webm");
      const res = await fetch("/api/episode-audio", { method: "POST", body: fd });
      const json = (await res.json()) as { success?: boolean; error?: string };
      if (!res.ok || !json.success) {
        throw new Error(json.error || "Error al subir");
      }
      setUploadMessage("Guardado como MP3 en la carpeta del episodio.");
      resetAfterSuccess();
      onUploaded();
    } catch (e) {
      setUploadMessage(
        e instanceof Error ? e.message : "Error al guardar en el servidor"
      );
    } finally {
      setUploading(false);
    }
  }, [
    episodeFolder,
    rawMp3Filename,
    finalBlob,
    resetAfterSuccess,
    onUploaded,
  ]);

  const ui =
    typeof document !== "undefined" ? (
      <div
        className="fixed inset-0 z-[300] flex flex-col bg-white text-gray-900"
        role="dialog"
        aria-modal="true"
        aria-label="Modo grabación"
      >
        <header className="flex shrink-0 flex-col gap-2 border-b border-gray-200 bg-white/95 px-4 py-3 backdrop-blur-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
            {!supported && (
              <p className="text-xs font-medium text-amber-800">
                La grabación en el navegador está disponible solo en{" "}
                <strong>Google Chrome</strong> para escritorio. Podés usar el
                modo lectura igualmente.
              </p>
            )}
            {supported && (
              <div className="flex flex-wrap items-center gap-2">
                {status === "idle" || status === "error" ? (
                  <button
                    type="button"
                    onClick={beginRecording}
                    disabled={uploading}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    <Mic size={16} aria-hidden />
                    Empezar a grabar
                  </button>
                ) : null}

                {status === "recording" ? (
                  <>
                    <button
                      type="button"
                      onClick={pauseRecording}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium hover:bg-gray-50"
                    >
                      <Pause size={16} aria-hidden />
                      Pausar
                    </button>
                    <button
                      type="button"
                      onClick={stopRecording}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800"
                    >
                      <Square size={14} aria-hidden />
                      Detener
                    </button>
                  </>
                ) : null}

                {status === "paused" ? (
                  <>
                    <button
                      type="button"
                      onClick={resumeRecording}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium hover:bg-gray-50"
                    >
                      <Play size={16} aria-hidden />
                      Reanudar
                    </button>
                    <button
                      type="button"
                      onClick={stopRecording}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800"
                    >
                      <Square size={14} aria-hidden />
                      Detener
                    </button>
                  </>
                ) : null}

                {status === "stopped" && finalBlob ? (
                  <>
                    <button
                      type="button"
                      onClick={() => void uploadMp3()}
                      disabled={uploading}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {uploading ? (
                        <Loader size={16} className="animate-spin" aria-hidden />
                      ) : (
                        <Upload size={16} aria-hidden />
                      )}
                      Guardar MP3 en episodio
                    </button>
                    <button
                      type="button"
                      onClick={downloadWebm}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium hover:bg-gray-50"
                    >
                      <Download size={16} aria-hidden />
                      Descargar WebM
                    </button>
                    <button
                      type="button"
                      onClick={discardSession}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
                    >
                      <Trash2 size={16} aria-hidden />
                      Descartar
                    </button>
                  </>
                ) : null}

                {(status === "recording" ||
                  status === "paused" ||
                  status === "requesting") && (
                  <button
                    type="button"
                    onClick={discardSession}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
                  >
                    <Trash2 size={16} aria-hidden />
                    Cancelar grabación
                  </button>
                )}
              </div>
            )}

            {supported && (
              <div className="flex flex-wrap items-center gap-3 text-sm text-gray-700">
                <span className="inline-flex items-center gap-1.5 font-mono text-base tabular-nums">
                  <Circle
                    size={10}
                    className={
                      status === "recording"
                        ? "fill-red-500 text-red-500"
                        : status === "paused"
                          ? "fill-amber-500 text-amber-500"
                          : "fill-gray-300 text-gray-300"
                    }
                    aria-hidden
                  />
                  {formatElapsed(elapsedSec)}
                </span>
                <RecordingLevelMeter stream={meterStream} />
                <span className="hidden text-xs text-gray-500 sm:inline">
                  → {rawMp3Filename}
                </span>
              </div>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {tabHidden && supported && isActive && (
              <span className="text-xs text-amber-700">
                Pestaña en segundo plano
              </span>
            )}
            <button
              type="button"
              onClick={tryClose}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-900 hover:bg-gray-50"
            >
              <X size={16} aria-hidden />
              Cerrar
            </button>
          </div>
        </header>

        {error && (
          <div className="shrink-0 border-b border-red-100 bg-red-50 px-4 py-2 text-sm text-red-800">
            {error}
          </div>
        )}
        {uploadMessage && (
          <div
            className={`shrink-0 border-b px-4 py-2 text-sm ${
              uploadMessage.startsWith("Guardado")
                ? "border-green-100 bg-green-50 text-green-900"
                : "border-amber-100 bg-amber-50 text-amber-900"
            }`}
          >
            {uploadMessage}
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto">
          <article
            className="recording-read mx-auto max-w-[40rem] px-6 py-10 pb-20 sm:px-10"
            dangerouslySetInnerHTML={{ __html: scriptHtml }}
          />
        </div>
      </div>
    ) : null;

  return ui && typeof document !== "undefined"
    ? createPortal(ui, document.body)
    : null;
}
