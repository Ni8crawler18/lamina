export default function Footer() {
  return (
    <footer className="border-t border-border/30 py-12 px-6">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2.5">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
            <path d="M14 22L4 16.5L14 11L24 16.5L14 22Z" fill="#5a3db5" opacity="0.6"/>
            <path d="M14 18L4 12.5L14 7L24 12.5L14 18Z" fill="#7c5ce7" opacity="0.8"/>
            <path d="M14 14L4 8.5L14 3L24 8.5L14 14Z" fill="#a78bfa"/>
          </svg>
          <span className="text-sm font-semibold">Laminaa</span>
          <span className="text-xs text-muted-foreground ml-2">Autonomous RWA lifecycle agent</span>
        </div>

        <div className="flex items-center gap-6 text-xs text-muted-foreground">
          <span>Hedera Hello Future Apex Hackathon 2026</span>
          <a
            href="https://github.com/Ni8crawler18/lamina"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
