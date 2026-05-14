"use client";

import { useEditor, EditorContent, Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import { Markdown } from "tiptap-markdown";
import { useEffect, useState } from "react";
import {
  Bold,
  Italic,
  Strikethrough,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Quote,
  Minus,
  Undo,
  Redo,
  Mic,
} from "lucide-react";
import { RecordingModeOverlay } from "./RecordingModeOverlay";

function getMarkdownFromEditor(editor: Editor): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (editor.storage as any).markdown.getMarkdown();
}

interface MarkdownEditorProps {
  content: string;
  onChange: (markdown: string) => void;
  /** Solo Script: muestra acceso al modo lectura para grabar. */
  showRecordingMode?: boolean;
  /** Carpeta del episodio (p. ej. Filosofia/001 …) para guardar el MP3 raw. */
  episodeFolder?: string;
  /** Nombre del archivo MP3 en disco, p. ej. F001-raw.mp3 */
  rawMp3Filename?: string;
  onRecordingUploaded?: () => void;
}

export function MarkdownEditor({
  content,
  onChange,
  showRecordingMode = false,
  episodeFolder,
  rawMp3Filename,
  onRecordingUploaded,
}: MarkdownEditorProps) {
  const [recordingOpen, setRecordingOpen] = useState(false);
  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "Empezá a escribir..." }),
      Markdown,
    ],
    content,
    onUpdate: ({ editor }) => {
      const md = getMarkdownFromEditor(editor);
      onChange(md);
    },
    editorProps: {
      attributes: {
        class: "tiptap prose prose-sm max-w-none focus:outline-none",
      },
    },
  });

  useEffect(() => {
    if (editor && content !== getMarkdownFromEditor(editor)) {
      editor.commands.setContent(content);
    }
  }, [content, editor]);

  useEffect(() => {
    if (!recordingOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [recordingOpen]);

  const wordCount = editor?.getText().split(/\s+/).filter(Boolean).length ?? 0;
  const charCount = editor?.getText().length ?? 0;

  if (!editor) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap gap-0.5">
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBold().run()}
          active={editor.isActive("bold")}
          title="Negrita"
        >
          <Bold size={16} />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleItalic().run()}
          active={editor.isActive("italic")}
          title="Cursiva"
        >
          <Italic size={16} />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleStrike().run()}
          active={editor.isActive("strike")}
          title="Tachado"
        >
          <Strikethrough size={16} />
        </ToolbarButton>
        <div className="w-px bg-gray-200 dark:bg-gray-700 mx-1" />
        <ToolbarButton
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 1 }).run()
          }
          active={editor.isActive("heading", { level: 1 })}
          title="Título 1"
        >
          <Heading1 size={16} />
        </ToolbarButton>
        <ToolbarButton
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 2 }).run()
          }
          active={editor.isActive("heading", { level: 2 })}
          title="Título 2"
        >
          <Heading2 size={16} />
        </ToolbarButton>
        <ToolbarButton
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 3 }).run()
          }
          active={editor.isActive("heading", { level: 3 })}
          title="Título 3"
        >
          <Heading3 size={16} />
        </ToolbarButton>
        <div className="w-px bg-gray-200 dark:bg-gray-700 mx-1" />
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          active={editor.isActive("bulletList")}
          title="Lista"
        >
          <List size={16} />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          active={editor.isActive("orderedList")}
          title="Lista numerada"
        >
          <ListOrdered size={16} />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          active={editor.isActive("blockquote")}
          title="Cita"
        >
          <Quote size={16} />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().setHorizontalRule().run()}
          active={false}
          title="Línea horizontal"
        >
          <Minus size={16} />
        </ToolbarButton>
        <div className="w-px bg-gray-200 dark:bg-gray-700 mx-1" />
        <ToolbarButton
          onClick={() => editor.chain().focus().undo().run()}
          active={false}
          title="Deshacer"
        >
          <Undo size={16} />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().redo().run()}
          active={false}
          title="Rehacer"
        >
          <Redo size={16} />
        </ToolbarButton>
        {showRecordingMode && (
          <>
            <div className="w-px bg-gray-200 dark:bg-gray-700 mx-1" />
            <button
              type="button"
              onClick={() => setRecordingOpen(true)}
              title="Modo grabación: vista amplia para leer mientras grabás"
              className="inline-flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            >
              <Mic size={14} />
              Modo grabación
            </button>
          </>
        )}
        </div>
        <div className="text-xs text-gray-400 whitespace-nowrap ml-3">
          {wordCount} palabras · {charCount} chars
        </div>
      </div>
      <EditorContent editor={editor} />
      {recordingOpen &&
        showRecordingMode &&
        episodeFolder &&
        rawMp3Filename && (
          <RecordingModeOverlay
            scriptHtml={editor.getHTML()}
            episodeFolder={episodeFolder}
            rawMp3Filename={rawMp3Filename}
            onClose={() => setRecordingOpen(false)}
            onUploaded={() => onRecordingUploaded?.()}
          />
        )}
    </div>
  );
}

function ToolbarButton({
  children,
  onClick,
  active,
  title,
}: {
  children: React.ReactNode;
  onClick: () => void;
  active: boolean;
  title: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`p-1.5 rounded transition-colors ${
        active
          ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
          : "text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:hover:text-white dark:hover:bg-gray-800"
      }`}
    >
      {children}
    </button>
  );
}
