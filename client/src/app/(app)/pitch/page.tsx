"use client";

import { useRef } from "react";
import { Maximize2, ExternalLink } from "lucide-react";

export default function PitchPage() {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const goFullscreen = () => {
    if (iframeRef.current?.requestFullscreen) {
      iframeRef.current.requestFullscreen();
    }
  };

  const openExternal = () => {
    window.open("/slides.html", "_blank");
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-8 py-3 border-b border-border/30">
        <span className="text-sm font-medium">Elevator Pitch &mdash; 8 Slides</span>
        <div className="flex items-center gap-2">
          <button
            onClick={goFullscreen}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/50 rounded-lg transition-all"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            Fullscreen
          </button>
          <button
            onClick={openExternal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-secondary/50 rounded-lg transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            New Tab
          </button>
        </div>
      </div>

      {/* Slides iframe */}
      <div className="flex-1">
        <iframe
          ref={iframeRef}
          src="/slides.html"
          title="Lamina Pitch Slides"
          className="w-full h-full border-0"
          allowFullScreen
        />
      </div>
    </div>
  );
}
