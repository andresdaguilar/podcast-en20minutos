import path from "path";
import { REPO_ROOT } from "./paths";
import { PODCAST_CONFIG } from "./types";

const ALLOWED_TOP_LEVEL = new Set(
  Object.values(PODCAST_CONFIG).map((c) => c.folder)
);

/**
 * Returns resolved absolute episode directory under REPO_ROOT, or null if unsafe/invalid.
 */
export function canonicalEpisodeDirectory(folder: string): string | null {
  if (!folder || typeof folder !== "string") return null;
  if (folder.includes("\0")) return null;
  const rootResolved = path.resolve(REPO_ROOT);
  const abs = path.resolve(rootResolved, folder);
  if (abs !== rootResolved && !abs.startsWith(rootResolved + path.sep)) {
    return null;
  }
  const rel = path.relative(rootResolved, abs);
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) return null;
  const first = rel.split(path.sep)[0];
  if (!ALLOWED_TOP_LEVEL.has(first)) return null;
  return abs;
}

export function isValidRawMp3Filename(name: string): boolean {
  if (!name || name.length > 200) return false;
  if (name.includes("/") || name.includes("\\") || name.includes("..")) {
    return false;
  }
  if (!/^[\w.-]+\.mp3$/i.test(name)) return false;
  if (!name.toLowerCase().includes("-raw")) return false;
  return true;
}
