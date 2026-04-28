"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    YT: typeof YT;
    onYouTubeIframeAPIReady: () => void;
  }
}

export default function ChatMockup() {
  const playerRef = useRef<HTMLDivElement>(null);
  const ytPlayerRef = useRef<YT.Player | null>(null);

  useEffect(() => {
    const initPlayer = () => {
      if (!playerRef.current || ytPlayerRef.current) return;
      ytPlayerRef.current = new window.YT.Player(playerRef.current, {
        videoId: "QGe_4rgVw6I",
        playerVars: {
          autoplay: 1,
          mute: 1,
          loop: 1,
          playlist: "QGe_4rgVw6I",
          controls: 0,
          showinfo: 0,
          rel: 0,
          modestbranding: 1,
          playsinline: 1,
        },
        events: {
          onReady: (event: YT.PlayerEvent) => {
            event.target.setPlaybackQuality("hd720");
            event.target.playVideo();
          },
        },
      });
    };

    if (window.YT && window.YT.Player) {
      initPlayer();
    } else {
      const tag = document.createElement("script");
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
      window.onYouTubeIframeAPIReady = initPlayer;
    }

    return () => {
      ytPlayerRef.current?.destroy();
      ytPlayerRef.current = null;
    };
  }, []);

  return (
    <section className="py-8 px-6 lg:px-[120px]">
      <div className="max-w-4xl mx-auto">
        <div className="bg-[#1E293B] rounded-xl border border-[#22D3EE20] overflow-hidden shadow-2xl">
          {/* 타이틀바 */}
          <div className="flex items-center gap-2 px-4 py-3 bg-[#0F172A] border-b border-[#1E293B]">
            <div className="w-3 h-3 rounded-full bg-[#EF4444]" />
            <div className="w-3 h-3 rounded-full bg-[#EAB308]" />
            <div className="w-3 h-3 rounded-full bg-[#22C55E]" />
            <span className="ml-3 text-xs text-[#475569] font-mono">tradecoach.ai/demo</span>
          </div>

          {/* YouTube 영상 (API 기반 720p 강제) */}
          <div className="relative w-full" style={{ paddingBottom: "56.25%" }}>
            <div ref={playerRef} className="absolute inset-0 w-full h-full" />
          </div>
        </div>
      </div>
    </section>
  );
}
