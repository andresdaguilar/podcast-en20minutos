import { NextRequest, NextResponse } from "next/server";
import { generateCompleteAudio } from "@/lib/ffmpeg";
import { PodcastId } from "@/lib/types";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { folder, podcast } = body as { folder: string; podcast: PodcastId };

    if (!folder || !podcast) {
      return NextResponse.json(
        { error: "Missing folder or podcast" },
        { status: 400 }
      );
    }

    const result = await generateCompleteAudio(folder, podcast);
    if (result.success) {
      return NextResponse.json({ success: true, output: result.output });
    } else {
      return NextResponse.json(
        { success: false, error: result.error },
        { status: 400 }
      );
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
