import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import os from "os";
import path from "path";
import { randomBytes } from "crypto";
import { REPO_ROOT } from "@/lib/paths";
import { convertWebmToMp3 } from "@/lib/ffmpeg";
import {
  canonicalEpisodeDirectory,
  isValidRawMp3Filename,
} from "@/lib/episodeUpload";
import {
  loadEpisodes,
  mergeScannedWithExisting,
  saveEpisodes,
  scanAll,
} from "@/lib/scanner";
import { applyDueScheduledPublishing } from "@/lib/episodeStatus";

export const maxDuration = 3600;

export async function POST(request: NextRequest) {
  let tempPath: string | null = null;
  try {
    const form = await request.formData();
    const folder = form.get("folder");
    const filename = form.get("filename");
    const file = form.get("file");

    if (typeof folder !== "string" || typeof filename !== "string") {
      return NextResponse.json(
        { error: "folder y filename son requeridos" },
        { status: 400 }
      );
    }

    if (!isValidRawMp3Filename(filename)) {
      return NextResponse.json(
        { error: "Nombre de archivo MP3 inválido (debe ser .mp3 e incluir -raw)" },
        { status: 400 }
      );
    }

    const epDir = canonicalEpisodeDirectory(folder);
    if (!epDir || !fs.existsSync(epDir)) {
      return NextResponse.json(
        { error: "Carpeta de episodio inválida o inexistente" },
        { status: 400 }
      );
    }

    if (!(file instanceof Blob) || file.size === 0) {
      return NextResponse.json(
        { error: "Archivo de audio vacío o inválido" },
        { status: 400 }
      );
    }

    const buf = Buffer.from(await file.arrayBuffer());
    const id = randomBytes(8).toString("hex");
    tempPath = path.join(os.tmpdir(), `podcast-rec-${id}.webm`);
    fs.writeFileSync(tempPath, buf);

    const outMp3 = path.join(epDir, filename);
    const conv = await convertWebmToMp3(tempPath, outMp3);
    if (!conv.success) {
      return NextResponse.json(
        { error: conv.error || "ffmpeg falló" },
        { status: 500 }
      );
    }

    const scanned = scanAll();
    const existing = loadEpisodes();
    const merged = mergeScannedWithExisting(scanned, existing);
    applyDueScheduledPublishing(merged);
    saveEpisodes(merged);

    return NextResponse.json({
      success: true,
      output: path.relative(REPO_ROOT, outMp3).replace(/\\/g, "/"),
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  } finally {
    if (tempPath && fs.existsSync(tempPath)) {
      try {
        fs.unlinkSync(tempPath);
      } catch {
        /* ignore */
      }
    }
  }
}
