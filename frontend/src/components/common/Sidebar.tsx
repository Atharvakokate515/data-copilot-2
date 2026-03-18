import React, { useState, useEffect } from "react";
import { PanelLeftClose, PanelLeft, Plus, Trash2, Clock, MessageSquare } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface Session {
  id: string | number;
  title: string;
  updated_at: string;
}

interface SidebarProps {
  sessions: Session[];
  activeId: string | number | null;
  onSelect: (id: string | number) => void;
  onDelete: (id: string | number) => void;
  onNewChat: () => void;
  loading?: boolean;
}

function timeAgo(date: string) {
  const diff = Date.now() - new Date(date).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const Sidebar: React.FC<SidebarProps> = ({ sessions, activeId, onSelect, onDelete, onNewChat, loading }) => {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const check = () => setCollapsed(window.innerWidth < 1024);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (collapsed) {
    return (
      <div className="flex flex-col items-center w-14 bg-card border-r border-border py-3 gap-2 shrink-0">
        <button onClick={() => setCollapsed(false)} className="p-2 rounded-[4px] text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200">
          <PanelLeft size={18} />
        </button>
        <Tooltip>
          <TooltipTrigger asChild>
            <button onClick={onNewChat} className="p-2 rounded-[4px] text-primary hover:bg-muted transition-all duration-200">
              <Plus size={18} />
            </button>
          </TooltipTrigger>
          <TooltipContent side="right">New Chat</TooltipContent>
        </Tooltip>
        <div className="w-8 h-px bg-border my-1" />
        {sessions.map((s) => (
          <Tooltip key={s.id}>
            <TooltipTrigger asChild>
              <button
                onClick={() => onSelect(s.id)}
                className={`p-2 rounded-[4px] transition-all duration-200 ${s.id === activeId ? "bg-primary/20 text-primary" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}
              >
                <MessageSquare size={16} />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">{s.title || "Untitled"}</TooltipContent>
          </Tooltip>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col w-[260px] bg-card border-r border-border shrink-0">
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        <span className="font-mono uppercase text-[11px] tracking-[0.15em] font-bold text-foreground">Chats</span>
        <div className="flex items-center gap-1">
          <button onClick={onNewChat} className="p-1.5 rounded-[4px] text-primary border border-muted-foreground/30 hover:bg-muted transition-all duration-200" title="New Chat">
            <Plus size={16} />
          </button>
          <button onClick={() => setCollapsed(true)} className="p-1.5 rounded-[4px] text-muted-foreground hover:text-foreground hover:bg-muted transition-all duration-200">
            <PanelLeftClose size={16} />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-thin py-1">
        {loading ? (
          <div className="px-3 py-2 space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-muted rounded-[4px] animate-pulse" />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <Clock size={24} className="mx-auto mb-2 text-muted-foreground/50" />
            <p className="font-mono uppercase text-[11px] tracking-[0.15em] text-muted-foreground">No chats yet</p>
          </div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`group flex items-center justify-between px-3 py-2.5 mx-1 rounded-[4px] cursor-pointer transition-all duration-200 ${
                s.id === activeId
                  ? "bg-muted border-l-2 border-primary"
                  : "hover:bg-muted/60 border-l-2 border-transparent"
              }`}
            >
              <div className="flex-1 min-w-0">
                <p className="font-mono text-[11px] tracking-[0.05em] text-foreground truncate">{s.title || "Untitled"}</p>
                <p className="font-mono text-[10px] text-muted-foreground">{timeAgo(s.updated_at)}</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(s.id); }}
                className="p-1 rounded-[4px] opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-200"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Sidebar;
