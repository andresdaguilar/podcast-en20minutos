import { exec } from "child_process";
import { promisify } from "util";
import fs from "fs";
import path from "path";
import { REPO_ROOT } from "./paths";
import { PODCAST_CONFIG, PodcastId } from "./types";

const execAsync = promisify(exec);

/** One sample rate / layout for the whole mux avoids acrossfade + libmp3lame errors. */
const COMPLETE_AUDIO_MIX_RATE = 44100;

/** Per-segment dynamics (garageband intro vs narración mono vs outro). */
const COMPLETE_AUDIO_DYNAUDNORM = "dynaudnorm=f=300:g=25";
/** Final integrated loudness (podcast / plataforma streaming típico). */
const COMPLETE_AUDIO_LOUDNORM = "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=none";

const VIDEO_OUT_SIZE = "1920:1080";
/** Exact frame size (stretches if source aspect ≠ 16:9; no letterboxing). */
const VIDEO_STILL_IMAGE_VF = `scale=${VIDEO_OUT_SIZE}`;

async function getAudioDuration(filePath: string): Promise<number> {
  const { stdout } = await execAsync(
    `ffprobe -v error -show_entries format=duration -of csv=p=0 "${filePath}"`
  );
  return parseFloat(stdout.trim());
}

function findFile(dir: string, pattern: RegExp): string | null {
  if (!fs.existsSync(dir)) return null;
  const files = fs.readdirSync(dir);
  const match = files.find((f) => pattern.test(f));
  return match ? path.join(dir, match) : null;
}

export function findIntroOutro(podcastId: PodcastId): {
  intro: string | null;
  outro: string | null;
} {
  const config = PODCAST_CONFIG[podcastId];
  const dir = path.join(REPO_ROOT, config.introOutroFolder);

  if (!fs.existsSync(dir)) return { intro: null, outro: null };

  const files = fs.readdirSync(dir);

  const introFile = files.find(
    (f) => /intro/i.test(f) && /\.(wav|mp3|m4a)$/i.test(f)
  );
  const outroFile = files.find(
    (f) => /outro/i.test(f) && /\.(wav|mp3|m4a)$/i.test(f)
  );

  return {
    intro: introFile ? path.join(dir, introFile) : null,
    outro: outroFile ? path.join(dir, outroFile) : null,
  };
}

export async function generateCompleteAudio(
  episodeFolder: string,
  podcastId: PodcastId
): Promise<{ success: boolean; output?: string; error?: string }> {
  const epDir = path.join(REPO_ROOT, episodeFolder);
  const { intro, outro } = findIntroOutro(podcastId);

  if (!intro || !outro) {
    return { success: false, error: "No se encontraron archivos de intro/outro" };
  }

  const enhancedFile = findFile(epDir, /enhanced.*\.mp3$/i);
  if (!enhancedFile) {
    return { success: false, error: "No se encontró el archivo enhanced.mp3" };
  }

  const prefix = PODCAST_CONFIG[podcastId].prefix;
  const folderName = path.basename(episodeFolder);
  const numMatch = folderName.match(/^(\d+)/);
  const numStr = numMatch ? numMatch[1].padStart(3, "0") : "000";
  const outputFile = path.join(epDir, `${prefix}${numStr}-completo.mp3`);

  try {
    const introDur = await getAudioDuration(intro);
    const fadeOutStart = Math.max(0, introDur - 1);
    const st = fadeOutStart.toFixed(6);

    const norm = `aresample=async=1:first_pts=0:osr=${COMPLETE_AUDIO_MIX_RATE},aformat=sample_fmts=fltp:channel_layouts=stereo`;

    const filterComplex =
      `[0:a]${norm},${COMPLETE_AUDIO_DYNAUDNORM},afade=t=out:st=${st}:d=1[a0];` +
      `[1:a]${norm},${COMPLETE_AUDIO_DYNAUDNORM}[a1];` +
      `[2:a]${norm},${COMPLETE_AUDIO_DYNAUDNORM},afade=t=in:st=0:d=1[a2];` +
      `[a0][a1]acrossfade=d=1:c1=tri:c2=tri[a01];` +
      `[a01][a2]acrossfade=d=1:c1=tri:c2=tri[pre];` +
      `[pre]${COMPLETE_AUDIO_LOUDNORM}[out]`;

    const cmd = [
      "ffmpeg -y",
      `-i "${intro}"`,
      `-i "${enhancedFile}"`,
      `-i "${outro}"`,
      `-filter_complex`,
      `"${filterComplex}"`,
      `-map "[out]"`,
      `-codec:a libmp3lame -b:a 192k`,
      `-ar ${COMPLETE_AUDIO_MIX_RATE}`,
      `"${outputFile}"`,
    ].join(" ");

    await execAsync(cmd, { timeout: 300000 });
    return { success: true, output: outputFile };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return { success: false, error: message };
  }
}

const RECORDING_MP3_RATE = 44100;

/**
 * Converts a browser WebM/Opus recording to mono MP3 for episode raw track.
 */
export async function convertWebmToMp3(
  inputWebmPath: string,
  outputMp3Path: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const cmd = [
      "ffmpeg -y",
      `-i "${inputWebmPath}"`,
      `-vn`,
      `-ac 1`,
      `-ar ${RECORDING_MP3_RATE}`,
      `-codec:a libmp3lame -b:a 192k`,
      `"${outputMp3Path}"`,
    ].join(" ");

    await execAsync(cmd, { timeout: 3_600_000 });
    return { success: true };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return { success: false, error: message };
  }
}

export async function generateVideo(
  episodeFolder: string,
  podcastId: PodcastId
): Promise<{ success: boolean; output?: string; error?: string }> {
  const epDir = path.join(REPO_ROOT, episodeFolder);
  const prefix = PODCAST_CONFIG[podcastId].prefix;
  const folderName = path.basename(episodeFolder);
  const numMatch = folderName.match(/^(\d+)/);
  const numStr = numMatch ? numMatch[1].padStart(3, "0") : "000";

  const coverFile = findFile(epDir, new RegExp(`${prefix}${numStr}Y\\.(jpg|jpeg|png|webp)$`, "i"));
  if (!coverFile) {
    return { success: false, error: "No se encontró el cover de YouTube (*Y.jpg/png)" };
  }

  const audioFile = findFile(epDir, /completo.*\.mp3$/i);
  if (!audioFile) {
    return { success: false, error: "No se encontró el audio completo (*-completo.mp3)" };
  }

  const outputFile = path.join(epDir, `${prefix}${numStr}-video.mp4`);

  try {
    const cmd = [
      "ffmpeg -y",
      `-loop 1 -i "${coverFile}"`,
      `-i "${audioFile}"`,
      `-vf "${VIDEO_STILL_IMAGE_VF},fps=30"`,
      `-c:v libx264 -tune stillimage`,
      `-c:a aac -b:a 192k`,
      `-pix_fmt yuv420p`,
      `-shortest`,
      `"${outputFile}"`,
    ].join(" ");

    await execAsync(cmd, { timeout: 600000 });
    return { success: true, output: outputFile };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return { success: false, error: message };
  }
}
