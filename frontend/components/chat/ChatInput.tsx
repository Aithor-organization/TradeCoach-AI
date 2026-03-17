"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import type { Language } from "@/stores/languageStore";
import { t } from "@/lib/i18n";
import ImagePreview from "./ImagePreview";

export default function ChatInput({ onSend, language = "ko" }: { onSend: (text: string, image?: File) => void; language?: Language }) {
  const [text, setText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { attachedImage, setAttachedImage, isLoading, pendingInput, setPendingInput } = useChatStore();

  // 외부에서 pendingInput이 설정되면 입력창에 반영
  useEffect(() => {
    if (pendingInput) {
      setText(pendingInput);
      setPendingInput(null);
    }
  }, [pendingInput, setPendingInput]);

  // 텍스트 양에 따라 textarea 높이 자동 조절 (최대 3배)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    // 기본 높이 44px, 최대 3배 = 132px
    el.style.height = Math.min(el.scrollHeight, 132) + "px";
  }, [text]);

  const handleSubmit = useCallback(() => {
    if ((!text.trim() && !attachedImage) || isLoading) return;

    onSend(text.trim(), attachedImage || undefined);
    setText("");
    setAttachedImage(null);
  }, [text, attachedImage, isLoading, onSend, setAttachedImage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) setAttachedImage(file);
        return;
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith("image/")) {
      setAttachedImage(file);
    }
    e.target.value = "";
  };

  return (
    <div className="border-t border-[#1E293B] bg-[#0F172A] p-4">
      {/* 이미지 미리보기 */}
      {attachedImage && (
        <ImagePreview file={attachedImage} onRemove={() => setAttachedImage(null)} />
      )}

      <div className="flex items-end gap-3">
        {/* 이미지 첨부 */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="w-10 h-10 flex-shrink-0 rounded-lg bg-[#1E293B] flex items-center justify-center text-[#94A3B8] hover:text-white hover:bg-[#22D3EE20] transition-colors cursor-pointer"
          title={t("input.attachImage", language)}
        >
          📎
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileSelect}
        />

        {/* 텍스트 입력 */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={t("input.placeholder", language)}
          className="flex-1 bg-[#1E293B] text-white text-sm rounded-lg px-4 py-3 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none resize-none min-h-[44px] placeholder-[#475569] overflow-y-auto"
          rows={1}
          disabled={isLoading}
        />

        {/* 전송 */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isLoading || (!text.trim() && !attachedImage)}
          className="w-10 h-10 flex-shrink-0 rounded-lg gradient-accent flex items-center justify-center text-[#0A0F1C] font-bold disabled:opacity-40 cursor-pointer transition-opacity"
        >
          {isLoading ? "⏳" : "↑"}
        </button>
      </div>
    </div>
  );
}
