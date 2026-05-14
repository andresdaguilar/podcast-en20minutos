import path from "path";

export const REPO_ROOT = path.resolve(
  process.cwd(),
  ".."
);

export const DATA_PATH = path.join(process.cwd(), "data", "episodes.json");

export function episodeFolderPath(folder: string): string {
  return path.join(REPO_ROOT, folder);
}
