"use client";

import { useEffect, useState } from "react";
import { useLanguageStore } from "@/stores/languageStore";
import { t } from "@/lib/i18n";

interface ImagePreviewProps {
  file: File;
  onRemove: () => void;
}

export default function ImagePreview({ file, onRemove }: ImagePreviewProps) {
  const [preview, setPreview] = useState<string>("");
  const { language } = useLanguageStore();

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  if (!preview) return null;

  return (
    <div className="mb-3 inline-block relative">
      <img
        src={preview}
        alt={t("cp.attachedImage", language)}
        className="h-20 rounded-lg border border-[#22D3EE30] object-cover"
      />
      <button
        type="button"
        onClick={onRemove}
        className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-[#EF4444] text-white text-xs flex items-center justify-center cursor-pointer hover:bg-[#DC2626]"
      >
        ×
      </button>
    </div>
  );
}
