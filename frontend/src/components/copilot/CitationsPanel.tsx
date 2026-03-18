import React, { useState } from "react";
import { ChevronDown, ChevronRight, FileText } from "lucide-react";
import type { Citation } from "@/types";

interface CitationsPanelProps {
  citations: Citation[];
  visible?: boolean;
}

const CitationsPanel: React.FC<CitationsPanelProps> = ({ citations, visible = true }) => {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="mt-3 border-t border-border pt-2 transition-transform duration-300"
      style={{ transform: visible ? "translateX(0)" : "translateX(100%)" }}
    >
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1.5 font-mono uppercase text-[10px] tracking-[0.15em] text-muted-foreground hover:text-foreground transition-all duration-200">
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span>SOURCES</span>
        <span className="ml-1 px-1.5 py-0.5 bg-primary/20 text-primary rounded-[2px] font-bold">{citations.length}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {citations.map((c, i) => (
            <div key={i} className="relative flex items-center gap-3 bg-muted rounded-[4px] px-3 py-2">
              <FileText size={14} className="text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="font-mono text-[11px] text-primary truncate">{c.source}</p>
                <p className="font-mono text-[10px] text-muted-foreground">Page {c.page}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <div className="w-16 h-1.5 bg-muted-foreground/20 rounded-[2px] overflow-hidden">
                  <div
                    className="h-full rounded-[2px] bg-primary"
                    style={{ width: `${c.confidence * 100}%` }}
                  />
                </div>
                <span className="font-mono text-[10px] text-muted-foreground w-8 text-right">{Math.round(c.confidence * 100)}%</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CitationsPanel;
