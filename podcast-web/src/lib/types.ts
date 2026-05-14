export type PodcastId = "filosofia" | "historia" | "libros" | "mitologia";

export interface EpisodeContent {
  script: boolean;
  blog: boolean;
  translations: string[];
}

export interface EpisodeImages {
  blog: boolean;
  spotify: boolean;
  youtube: boolean;
}

export interface EpisodeAudio {
  raw: boolean;
  enhanced: boolean;
  complete: boolean;
}

export interface Episode {
  number: number;
  title: string;
  folder: string;
  publishDate: string | null;
  published: boolean;
  content: EpisodeContent;
  hasDescriptions: boolean;
  images: EpisodeImages;
  audio: EpisodeAudio;
  hasVideo: boolean;
}

export interface EpisodesData {
  filosofia: Episode[];
  historia: Episode[];
  libros: Episode[];
  mitologia: Episode[];
}

export interface Descriptions {
  [lang: string]: string;
}

export const PODCAST_CONFIG: Record<
  PodcastId,
  { label: string; prefix: string; folder: string; introOutroFolder: string }
> = {
  filosofia: {
    label: "Filosofía",
    prefix: "F",
    folder: "Filosofia",
    introOutroFolder: "Filosofia/000 Resources",
  },
  historia: {
    label: "Historia",
    prefix: "H",
    folder: "Historia",
    introOutroFolder:
      "Historia/000 Recursos comunes/Template completo.band/Media/Audio Files",
  },
  libros: {
    label: "Libros",
    prefix: "L",
    folder: "Libros",
    introOutroFolder:
      "Libros/000 Recursos comunes/Template 2.band/Media/Audio Files",
  },
  mitologia: {
    label: "Mitología",
    prefix: "M",
    folder: "Mitologia",
    introOutroFolder:
      "Mitologia/000 Recursos comunes/Template 2.band/Media/Audio Files",
  },
};
