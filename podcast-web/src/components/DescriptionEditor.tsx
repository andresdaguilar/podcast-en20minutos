"use client";

import { useEffect, useState, useCallback } from "react";
import { Descriptions } from "@/lib/types";
import { Save, Copy, Check, Plus } from "lucide-react";

const MAX_LENGTH = 250;

interface DescriptionEditorProps {
  folder: string;
}

const LANGUAGE_OPTIONS = [
  { code: "es", label: "Español" },
  { code: "en", label: "English" },
  { code: "pt", label: "Português" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
];

export function DescriptionEditor({ folder }: DescriptionEditorProps) {
  const [descriptions, setDescriptions] = useState<Descriptions>({});
  const [originalDescriptions, setOriginalDescriptions] = useState<Descriptions>({});
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [showAddLang, setShowAddLang] = useState(false);

  const loadDescriptions = useCallback(async () => {
    const params = new URLSearchParams({ folder });
    const res = await fetch(`/api/descriptions?${params}`);
    const json = await res.json();
    setDescriptions(json.descriptions || {});
    setOriginalDescriptions(json.descriptions || {});
  }, [folder]);

  useEffect(() => {
    loadDescriptions();
  }, [loadDescriptions]);

  const handleSave = async () => {
    setSaving(true);
    await fetch("/api/descriptions", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder, descriptions }),
    });
    setOriginalDescriptions({ ...descriptions });
    setSaving(false);
  };

  const handleCopy = (lang: string) => {
    navigator.clipboard.writeText(descriptions[lang] || "");
    setCopied(lang);
    setTimeout(() => setCopied(null), 2000);
  };

  const addLanguage = (code: string) => {
    setDescriptions((prev) => ({ ...prev, [code]: "" }));
    setShowAddLang(false);
  };

  const hasChanges =
    JSON.stringify(descriptions) !== JSON.stringify(originalDescriptions);

  const activeLangs = Object.keys(descriptions);
  const availableLangs = LANGUAGE_OPTIONS.filter(
    (l) => !activeLangs.includes(l.code)
  );

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
      <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-800 px-4 py-3">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">
          Descripciones (max {MAX_LENGTH} chars)
        </h3>
        <div className="flex items-center gap-2">
          {availableLangs.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setShowAddLang(!showAddLang)}
                className="flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-900 dark:hover:text-white border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <Plus size={12} /> Idioma
              </button>
              {showAddLang && (
                <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10 py-1 min-w-[120px]">
                  {availableLangs.map((lang) => (
                    <button
                      key={lang.code}
                      onClick={() => addLanguage(lang.code)}
                      className="block w-full text-left px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <button
            onClick={handleSave}
            disabled={!hasChanges || saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save size={14} />
            {saving ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {activeLangs.length === 0 ? (
          <div className="text-center py-4 text-gray-500 text-sm">
            No hay descripciones. Agregá un idioma para empezar.
          </div>
        ) : (
          activeLangs.map((lang) => {
            const langLabel =
              LANGUAGE_OPTIONS.find((l) => l.code === lang)?.label || lang.toUpperCase();
            const charCount = (descriptions[lang] || "").length;
            const isOver = charCount > MAX_LENGTH;

            return (
              <div key={lang}>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-gray-500 uppercase">
                    {langLabel}
                  </label>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs ${
                        isOver ? "text-red-500 font-bold" : "text-gray-400"
                      }`}
                    >
                      {charCount}/{MAX_LENGTH}
                    </span>
                    <button
                      onClick={() => handleCopy(lang)}
                      className="p-1 text-gray-400 hover:text-gray-700 dark:hover:text-white rounded transition-colors"
                      title="Copiar"
                    >
                      {copied === lang ? (
                        <Check size={14} className="text-green-500" />
                      ) : (
                        <Copy size={14} />
                      )}
                    </button>
                  </div>
                </div>
                <textarea
                  value={descriptions[lang] || ""}
                  onChange={(e) =>
                    setDescriptions((prev) => ({
                      ...prev,
                      [lang]: e.target.value,
                    }))
                  }
                  rows={3}
                  className={`w-full px-3 py-2 border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-800 dark:text-white ${
                    isOver
                      ? "border-red-300 dark:border-red-700"
                      : "border-gray-200 dark:border-gray-700"
                  }`}
                  placeholder={`Descripción en ${langLabel} (max ${MAX_LENGTH} caracteres)`}
                />
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
