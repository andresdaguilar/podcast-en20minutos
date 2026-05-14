import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { episodeFolderPath } from "@/lib/paths";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const folder = searchParams.get("folder");
  const file = searchParams.get("file");

  if (!folder || !file) {
    return NextResponse.json({ error: "Missing folder or file param" }, { status: 400 });
  }

  const filePath = path.join(episodeFolderPath(folder), file);

  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ content: "", exists: false });
  }

  const content = fs.readFileSync(filePath, "utf-8");
  return NextResponse.json({ content, exists: true });
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { folder, file, content } = body as {
      folder: string;
      file: string;
      content: string;
    };

    if (!folder || !file) {
      return NextResponse.json({ error: "Missing folder or file" }, { status: 400 });
    }

    const dirPath = episodeFolderPath(folder);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }

    const filePath = path.join(dirPath, file);
    fs.writeFileSync(filePath, content, "utf-8");

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
