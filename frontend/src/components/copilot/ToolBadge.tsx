import React from "react";

interface ToolBadgeProps {
  tool: string;
  sqlUsed?: boolean;
  ragUsed?: boolean;
}

const ToolBadge: React.FC<ToolBadgeProps> = ({ tool, sqlUsed, ragUsed }) => {
  if (tool === "synthesis") {
    return (
      <div className="flex items-center gap-1.5">
        {sqlUsed && (
          <span className="inline-flex items-center font-mono uppercase text-[9px] tracking-[0.15em] px-2 py-0.5 rounded-[2px] bg-card text-primary">
            [ SQL ]
          </span>
        )}
        {ragUsed && (
          <span className="inline-flex items-center font-mono uppercase text-[9px] tracking-[0.15em] px-2 py-0.5 rounded-[2px] bg-card text-muted-foreground">
            [ RAG ]
          </span>
        )}
      </div>
    );
  }

  if (tool === "chat") {
    return (
      <span className="inline-flex items-center font-mono uppercase text-[9px] tracking-[0.15em] px-2 py-0.5 rounded-[2px] bg-card text-border">
        [ CHAT ]
      </span>
    );
  }

  return null;
};

export default ToolBadge;
