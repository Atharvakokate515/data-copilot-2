import React, { useState } from "react";
import { AlertTriangle, Zap } from "lucide-react";
import type { Message } from "@/types";
import CitationsPanel from "@/components/copilot/CitationsPanel";
import ToolBadge from "@/components/copilot/ToolBadge";

interface ChatMessageProps {
  message: Message;
  onClarificationSubmit?: (response: string) => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, onClarificationSubmit }) => {
  const [clarifyInput, setClarifyInput] = useState("");

  if (message.role === "user") {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="relative max-w-[75%] bg-card border border-border rounded-[4px] px-4 py-2.5 text-sm font-mono text-foreground">
          <span className="absolute top-1 right-2 font-mono uppercase text-[9px] tracking-[0.15em] text-muted-foreground">YOU</span>
          <div className="mt-3">{message.content}</div>
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="flex justify-start animate-fade-in">
        <div className="max-w-[80%] bg-card border border-destructive/50 rounded-[4px] px-4 py-3">
          {message.metadata?.errorCode && (
            <span className="inline-block px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.1em] rounded-[2px] bg-destructive/20 text-destructive mb-2">
              {message.metadata.errorCode}
            </span>
          )}
          <p className="text-sm font-mono text-destructive">{message.content}</p>
        </div>
      </div>
    );
  }

  if (message.role === "clarification") {
    return (
      <div className="flex justify-start animate-fade-in">
        <div className="max-w-[80%] bg-card border border-warning/50 rounded-[4px] px-4 py-3">
          <div className="flex items-center gap-2 mb-2 text-warning text-[10px] font-mono uppercase tracking-[0.15em] font-bold">
            <AlertTriangle size={14} /> Clarification needed
          </div>
          <p className="text-sm font-mono text-foreground mb-3">{message.content}</p>
          {onClarificationSubmit && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (clarifyInput.trim()) {
                  onClarificationSubmit(clarifyInput.trim());
                  setClarifyInput("");
                }
              }}
              className="flex gap-2"
            >
              <input
                value={clarifyInput}
                onChange={(e) => setClarifyInput(e.target.value)}
                className="flex-1 bg-muted border border-border rounded-[4px] px-3 py-1.5 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                placeholder="Type your response..."
              />
              <button type="submit" className="px-3 py-1.5 bg-warning text-warning-foreground text-sm font-mono uppercase text-[10px] tracking-[0.1em] rounded-[4px] hover:bg-warning/90 transition-all duration-200">
                Reply
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex justify-start gap-3 animate-fade-in">
      {/* DM Avatar */}
      <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center shrink-0 mt-1">
        <span className="font-mono font-bold text-[9px] text-primary-foreground">DM</span>
      </div>
      <div className="max-w-[80%]">
        <p className="text-sm font-mono text-muted-foreground whitespace-pre-wrap">{message.content}</p>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          {message.metadata?.wasRetried && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.1em] rounded-[2px] bg-warning/20 text-warning">
              <Zap size={12} /> Retried
            </span>
          )}
          {message.metadata?.tool && (
            <ToolBadge tool={message.metadata.tool} sqlUsed={message.metadata.sqlUsed} ragUsed={message.metadata.ragUsed} />
          )}
          {message.metadata?.answerGrounded === false && message.metadata?.ragUsed && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.1em] rounded-[2px] bg-warning/20 text-warning">
              <AlertTriangle size={12} /> Ungrounded
            </span>
          )}
        </div>
        {message.metadata?.citations && message.metadata.citations.length > 0 && (
          <CitationsPanel citations={message.metadata.citations} visible />
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
