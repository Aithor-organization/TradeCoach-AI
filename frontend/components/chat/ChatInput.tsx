"use client";

import { useState, useRef, useCallback } from "react";
import { useChatStore } from "@/stores/chatStore";
import ImagePreview from "./ImagePreview";

export default function ChatInput({ onSend }: { onSend: (text: string, image?: File) => void }) {
  const [text, setText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { attachedImage, setAttachedImage, isLoading } = useChatStore();

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
          title="이미지 첨부"
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
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder="트레이딩 전략을 설명해주세요... (이미지 Ctrl+V 가능)"
          className="flex-1 bg-[#1E293B] text-white text-sm rounded-lg px-4 py-3 border border-[#47556933] focus:border-[#22D3EE50] focus:outline-none resize-none min-h-[44px] max-h-32 placeholder-[#475569]"
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
