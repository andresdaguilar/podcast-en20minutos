import fs from "fs";
import path from "path";
import { REPO_ROOT, DATA_PATH } from "./paths";
import {
  Episode,
  EpisodesData,
  PodcastId,
  PODCAST_CONFIG,
} from "./types";

function detectFiles(dirPath: string, prefix: string, num: string) {
  const files = fs.existsSync(dirPath) ? fs.readdirSync(dirPath) : [];
  const lower = files.map((f) => f.toLowerCase());

  const hasScript =
    files.some((f) => f.toLowerCase() === "script.md") ||
    files.some((f) => f.match(/^\d+-.*\.md$/) !== null);
  const hasBlog = files.some((f) => f.toLowerCase() === "blog.md");
  const translations = files
    .filter((f) => /^blog_([a-z]{2})\.md$/i.test(f))
    .map((f) => f.match(/^blog_([a-z]{2})\.md$/i)![1].toLowerCase());

  const hasDescriptions = files.some(
    (f) => f.toLowerCase() === "descriptions.json"
  );

  const pNum = `${prefix}${num}`.toLowerCase();

  const hasImageBlog = lower.some(
    (f) => f.startsWith(pNum + "b.") && /\.(jpg|jpeg|png|webp)$/.test(f)
  );
  const hasImageSpotify = lower.some(
    (f) => f.startsWith(pNum + "s.") && /\.(jpg|jpeg|png|webp)$/.test(f)
  );
  const hasImageYoutube = lower.some(
    (f) => f.startsWith(pNum + "y.") && /\.(jpg|jpeg|png|webp)$/.test(f)
  );

  const hasRaw = lower.some(
    (f) => f.includes("-raw") && f.endsWith(".mp3")
  );
  const hasEnhanced = lower.some(
    (f) => f.includes("enhanced") && f.endsWith(".mp3")
  );
  const hasComplete = lower.some(
    (f) => f.includes("completo") && f.endsWith(".mp3")
  );

  const hasVideo = lower.some((f) => f.endsWith(".mp4"));

  return {
    content: { script: hasScript, blog: hasBlog, translations },
    hasDescriptions,
    images: { blog: hasImageBlog, spotify: hasImageSpotify, youtube: hasImageYoutube },
    audio: { raw: hasRaw, enhanced: hasEnhanced, complete: hasComplete },
    hasVideo,
  };
}

function extractTitle(folderName: string): string {
  return folderName.replace(/^\d+\s*-?\s*/, "").trim();
}

function extractNumber(folderName: string): number {
  const match = folderName.match(/^(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

export function scanPodcast(podcastId: PodcastId): Episode[] {
  const config = PODCAST_CONFIG[podcastId];
  const podcastDir = path.join(REPO_ROOT, config.folder);

  if (!fs.existsSync(podcastDir)) return [];

  const entries = fs.readdirSync(podcastDir, { withFileTypes: true });
  const episodes: Episode[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    if (entry.name.startsWith("000") || entry.name.startsWith("_")) continue;

    const num = extractNumber(entry.name);
    if (num === 0) continue;

    const numStr = num.toString().padStart(3, "0");
    const dirPath = path.join(podcastDir, entry.name);
    const detected = detectFiles(dirPath, config.prefix, numStr);

    episodes.push({
      number: num,
      title: extractTitle(entry.name),
      folder: `${config.folder}/${entry.name}`,
      publishDate: null,
      published: false,
      ...detected,
    });
  }

  episodes.sort((a, b) => a.number - b.number);
  return episodes;
}

export function scanAll(): EpisodesData {
  return {
    filosofia: scanPodcast("filosofia"),
    historia: scanPodcast("historia"),
    libros: scanPodcast("libros"),
    mitologia: scanPodcast("mitologia"),
  };
}

export function loadEpisodes(): EpisodesData {
  if (fs.existsSync(DATA_PATH)) {
    const raw = fs.readFileSync(DATA_PATH, "utf-8");
    return JSON.parse(raw);
  }
  return { filosofia: [], historia: [], libros: [], mitologia: [] };
}

export function saveEpisodes(data: EpisodesData): void {
  const dir = path.dirname(DATA_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(DATA_PATH, JSON.stringify(data, null, 2), "utf-8");
}

export function mergeScannedWithExisting(
  scanned: EpisodesData,
  existing: EpisodesData
): EpisodesData {
  const result: EpisodesData = { filosofia: [], historia: [], libros: [], mitologia: [] };

  for (const podcastId of Object.keys(scanned) as PodcastId[]) {
    const scannedEps = scanned[podcastId];
    const existingEps = existing[podcastId];

    result[podcastId] = scannedEps.map((ep) => {
      const prev = existingEps.find((e) => e.number === ep.number);
      if (prev) {
        return {
          ...ep,
          publishDate: prev.publishDate,
          published: prev.published,
        };
      }
      return ep;
    });
  }

  return result;
}
