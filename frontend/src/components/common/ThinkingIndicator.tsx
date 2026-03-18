const ThinkingIndicator = () => (
  <div className="flex items-center gap-3 animate-fade-in">
    <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center shrink-0">
      <span className="font-mono font-bold text-[9px] text-primary-foreground">DM</span>
    </div>
    <div>
      <div className="flex items-center gap-1 font-mono uppercase text-[11px] tracking-[0.15em] text-muted-foreground">
        <span>PROCESSING</span>
        <span className="animate-pulse-dot">.</span>
        <span className="animate-pulse-dot [animation-delay:0.2s]">.</span>
        <span className="animate-pulse-dot [animation-delay:0.4s]">.</span>
      </div>
      <div className="mt-1.5 w-32 h-[2px] bg-muted rounded-[1px] overflow-hidden">
        <div className="h-full bg-primary rounded-[1px] origin-left animate-pulse-bar" />
      </div>
    </div>
  </div>
);

export default ThinkingIndicator;
