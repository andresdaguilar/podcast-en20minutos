import { NextRequest, NextResponse } from "next/server";
import { loadEpisodes, saveEpisodes } from "@/lib/scanner";
import { PodcastId } from "@/lib/types";
import { applyDueScheduledPublishing, utcDateISO } from "@/lib/episodeStatus";

export async function GET() {
  try {
    const data = loadEpisodes();
    if (applyDueScheduledPublishing(data)) {
      saveEpisodes(data);
    }
    return NextResponse.json(data);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { podcast, number, updates } = body as {
      podcast: PodcastId;
      number: number;
      updates: { publishDate?: string | null; published?: boolean };
    };

    const data = loadEpisodes();
    const episode = data[podcast].find((ep) => ep.number === number);
    if (!episode) {
      return NextResponse.json({ error: "Episode not found" }, { status: 404 });
    }

    if (updates.published === true) {
      episode.published = true;
      episode.publishDate =
        updates.publishDate !== undefined && updates.publishDate !== null
          ? updates.publishDate
          : utcDateISO();
    } else {
      if (updates.published === false) {
        episode.published = false;
      }
      if (updates.publishDate !== undefined) {
        episode.publishDate = updates.publishDate;
      }
    }

    applyDueScheduledPublishing(data);
    saveEpisodes(data);
    return NextResponse.json({ success: true, episode });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
