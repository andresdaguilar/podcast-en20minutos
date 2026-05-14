import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { episodeFolderPath } from "@/lib/paths";
import { Descriptions } from "@/lib/types";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const folder = searchParams.get("folder");

  if (!folder) {
    return NextResponse.json({ error: "Missing folder param" }, { status: 400 });
  }

  const filePath = path.join(episodeFolderPath(folder), "descriptions.json");

  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ descriptions: {} });
  }

  const raw = fs.readFileSync(filePath, "utf-8");
  const descriptions: Descriptions = JSON.parse(raw);
  return NextResponse.json({ descriptions });
}

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { folder, descriptions } = body as {
      folder: string;
      descriptions: Descriptions;
    };

    if (!folder) {
      return NextResponse.json({ error: "Missing folder" }, { status: 400 });
    }

    const dirPath = episodeFolderPath(folder);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }

    const filePath = path.join(dirPath, "descriptions.json");
    fs.writeFileSync(filePath, JSON.stringify(descriptions, null, 2), "utf-8");

    return NextResponse.json({ success: true });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
