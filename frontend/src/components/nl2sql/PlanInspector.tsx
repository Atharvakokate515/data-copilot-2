import React, { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { Plan } from "@/types";

interface PlanInspectorProps {
  plan: Plan;
}

const PlanInspector: React.FC<PlanInspectorProps> = ({ plan }) => {
  const [open, setOpen] = useState(false);

  const pad = (n: number) => String(n).padStart(2, "0");

  return (
    <div className="border-t border-border">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 w-full px-4 py-2 font-mono uppercase text-[10px] tracking-[0.15em] text-muted-foreground hover:text-foreground transition-all duration-200">
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Query Plan
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-1 font-mono text-[11px]">
          <div className="flex">
            <span className="text-muted-foreground">[{pad(1)}]</span>
            <span className="text-muted-foreground mx-2">INTENT</span>
            <span className="text-muted-foreground">{"·".repeat(12)}</span>
            <span className="ml-2 text-foreground">{plan.intent}</span>
          </div>
          <div className="flex">
            <span className="text-muted-foreground">[{pad(2)}]</span>
            <span className="text-muted-foreground mx-2">TABLES</span>
            <span className="text-muted-foreground">{"·".repeat(12)}</span>
            <span className="ml-2 text-foreground">{plan.tables.join(", ")}</span>
          </div>
          <div className="flex">
            <span className="text-muted-foreground">[{pad(3)}]</span>
            <span className="text-muted-foreground mx-2">COLUMNS</span>
            <span className="text-muted-foreground">{"·".repeat(11)}</span>
            <span className="ml-2 text-foreground">{plan.columns.join(", ")}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlanInspector;
