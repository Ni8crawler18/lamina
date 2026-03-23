export default function Footer() {
  return (
    <footer className="border-t border-border/30 py-12 px-6">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2.5">
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="#8259ef" />
            <path d="M8 9.5h4.5v9H8v-2.25h2.25v-4.5H8V9.5zM15.5 9.5H20v2.25h-2.25v4.5H20v2.25h-4.5v-9z" fill="white" />
          </svg>
          <span className="text-sm font-semibold">Lamina</span>
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
