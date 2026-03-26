"use client";

import { useState, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

interface PortalTooltipProps {
  text: string;
}

export default function PortalTooltip({ text }: PortalTooltipProps) {
  const [show, setShow] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const ref = useRef<HTMLSpanElement>(null);

  const handleEnter = useCallback(() => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      setPos({ x: rect.left + rect.width / 2, y: rect.top });
    }
    setShow(true);
  }, []);

  return (
    <>
      <span
        ref={ref}
        className="inline-flex ml-1 cursor-help"
        onMouseEnter={handleEnter}
        onMouseLeave={() => setShow(false)}
      >
        <span className="w-3.5 h-3.5 rounded-full bg-[#475569]/30 text-[#94A3B8] text-[9px] font-bold inline-flex items-center justify-center leading-none">?</span>
      </span>
      {show && typeof document !== "undefined" && createPortal(
        <div
          className="fixed px-2.5 py-1.5 rounded-md bg-[#0F172A] border border-[#22D3EE30] text-[10px] text-[#94A3B8] w-52 shadow-lg leading-relaxed whitespace-normal pointer-events-none"
          style={{
            left: pos.x,
            top: pos.y,
            transform: "translate(-50%, -100%) translateY(-6px)",
            zIndex: 99999,
          }}
        >
          {text}
        </div>,
        document.body,
      )}
    </>
  );
}
