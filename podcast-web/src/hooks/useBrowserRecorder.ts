"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderStatus =
  | "idle"
  | "requesting"
  | "recording"
  | "paused"
  | "stopped"
  | "error";

const PREFERRED_MIME = "audio/webm;codecs=opus";
const FALLBACK_MIME = "audio/webm";

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") return FALLBACK_MIME;
  if (MediaRecorder.isTypeSupported(PREFERRED_MIME)) return PREFERRED_MIME;
  return FALLBACK_MIME;
}

export function useBrowserRecorder() {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [finalBlob, setFinalBlob] = useState<Blob | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [meterStream, setMeterStream] = useState<MediaStream | null>(null);

  const chunksRef = useRef<BlobPart[]>([]);
  const mimeTypeRef = useRef<string>(FALLBACK_MIME);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const totalPausedMsRef = useRef(0);
  const pauseStartRef = useRef<number | null>(null);
  const recordStartRef = useRef<number | null>(null);

  const clearTick = useCallback(() => {
    if (tickRef.current !== null) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setMeterStream(null);
  }, []);

  const cleanupRecorder = useCallback(() => {
    clearTick();
    mediaRecorderRef.current = null;
    pauseStartRef.current = null;
    recordStartRef.current = null;
    totalPausedMsRef.current = 0;
    stopTracks();
  }, [clearTick, stopTracks]);

  const startRecording = useCallback(async () => {
    setError(null);
    setFinalBlob(null);
    chunksRef.current = [];
    setElapsedSec(0);
    setStatus("requesting");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;
      setMeterStream(stream);

      const mime = pickMimeType();
      mimeTypeRef.current = mime;
      const rec = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorderRef.current = rec;

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      rec.onerror = () => {
        setError("Error del MediaRecorder");
        setStatus("error");
        cleanupRecorder();
      };

      rec.onstop = () => {
        stopTracks();
        const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current });
        setFinalBlob(blob);
        setStatus("stopped");
        mediaRecorderRef.current = null;
      };

      totalPausedMsRef.current = 0;
      pauseStartRef.current = null;
      recordStartRef.current = performance.now();

      rec.start(1000);
      setStatus("recording");

      tickRef.current = setInterval(() => {
        if (pauseStartRef.current !== null) return;
        if (recordStartRef.current === null) return;
        const elapsed =
          (performance.now() -
            recordStartRef.current -
            totalPausedMsRef.current) /
          1000;
        setElapsedSec(Math.floor(elapsed));
      }, 400);
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : "No se pudo acceder al micrófono";
      setError(msg);
      setStatus("error");
      cleanupRecorder();
    }
  }, [cleanupRecorder, stopTracks]);

  const pauseRecording = useCallback(() => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state === "recording") {
      rec.pause();
      pauseStartRef.current = performance.now();
      setStatus("paused");
    }
  }, []);

  const resumeRecording = useCallback(() => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state === "paused") {
      if (pauseStartRef.current !== null) {
        totalPausedMsRef.current += performance.now() - pauseStartRef.current;
        pauseStartRef.current = null;
      }
      rec.resume();
      setStatus("recording");
    }
  }, []);

  const stopRecording = useCallback(() => {
    clearTick();
    const rec = mediaRecorderRef.current;
    if (rec && rec.state !== "inactive") {
      rec.stop();
    } else {
      stopTracks();
      setStatus((s) => (s === "requesting" ? "idle" : s));
    }
  }, [clearTick, stopTracks]);

  const discardSession = useCallback(() => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state !== "inactive") {
      clearTick();
      rec.onstop = () => {
        stopTracks();
        chunksRef.current = [];
        setFinalBlob(null);
        setStatus("idle");
        mediaRecorderRef.current = null;
      };
      try {
        rec.stop();
      } catch {
        cleanupRecorder();
        chunksRef.current = [];
        setFinalBlob(null);
        setStatus("idle");
      }
      return;
    }
    cleanupRecorder();
    chunksRef.current = [];
    setFinalBlob(null);
    setStatus("idle");
    setError(null);
  }, [clearTick, cleanupRecorder, stopTracks]);

  const resetAfterSuccess = useCallback(() => {
    cleanupRecorder();
    chunksRef.current = [];
    setFinalBlob(null);
    setError(null);
    setElapsedSec(0);
    setStatus("idle");
  }, [cleanupRecorder]);

  useEffect(() => {
    return () => {
      const rec = mediaRecorderRef.current;
      if (rec && rec.state !== "inactive") {
        try {
          rec.stop();
        } catch {
          /* ignore */
        }
      }
      clearTick();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [clearTick]);

  const hasPendingBlob = status === "stopped" && finalBlob !== null;

  return {
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
    isActive: status === "recording" || status === "paused",
  };
}
