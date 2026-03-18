import React, { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "sonner";
import { ChevronDown } from "lucide-react";
import Sidebar from "@/components/common/Sidebar";
import ChatMessage from "@/components/common/ChatMessage";
import ChatInput from "@/components/common/ChatInput";
import ThinkingIndicator from "@/components/common/ThinkingIndicator";
import DocUploadModal from "@/components/copilot/DocUploadModal";
import CitationsPanel from "@/components/copilot/CitationsPanel";
import Navbar from "@/components/common/Navbar";
import { createChat, agentChat, getCopilotSessions, getCopilotHistory, deleteCopilotSession } from "@/api/client";
import type { Message, CopilotSession } from "@/types";

const Copilot: React.FC = () => {
  const [showModal, setShowModal] = useState(true);
  const [chatId, setChatId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<CopilotSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [thinking, setThinking] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const scrollToBottom = () => chatEndRef.current?.scrollIntoView({ behavior: "smooth" });

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await getCopilotSessions();
      setSessions(data);
    } catch { /* ignore */ }
    setSessionsLoading(false);
  }, []);

  useEffect(() => { if (!showModal) fetchSessions(); }, [showModal, fetchSessions]);
  useEffect(scrollToBottom, [messages, thinking]);

  useEffect(() => {
    const el = chatContainerRef.current;
    if (!el) return;
    const handleScroll = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
      setShowScrollBtn(!atBottom);
    };
    el.addEventListener("scroll", handleScroll);
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  const handleNewChat = async () => {
    try {
      const res = await createChat("New Copilot Chat");
      setChatId(res.chat_id);
      setMessages([]);
      fetchSessions();
    } catch (err: any) {
      toast.error("Failed to create chat");
    }
  };

  const handleSelectSession = async (id: string | number) => {
    try {
      const data = await getCopilotHistory(id as number);
      setChatId(id as number);
      const restored: Message[] = data.messages.map((m: any, i: number) => ({
        id: `restored-${i}`,
        role: m.role === "user" ? "user" : "assistant",
        content: m.content,
      }));
      setMessages(restored);
    } catch {
      toast.error("Failed to load session");
    }
  };

  const handleDeleteSession = async (id: string | number) => {
    setSessions((prev) => prev.filter((s) => s.chat_id !== id));
    try { await deleteCopilotSession(id as number); } catch { fetchSessions(); }
    if (chatId === id) {
      setChatId(null);
      setMessages([]);
    }
  };

  const handleSend = async (text: string) => {
    let currentChatId = chatId;
    if (!currentChatId) {
      try {
        const res = await createChat("New Copilot Chat");
        currentChatId = res.chat_id;
        setChatId(currentChatId);
      } catch {
        toast.error("Failed to create chat");
        return;
      }
    }

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setThinking(true);

    try {
      const res = await agentChat("", text, currentChatId!);
      if (res.success) {
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.response.answer,
          metadata: {
            tool: res.response.tool,
            sqlUsed: res.response.sql_used,
            ragUsed: res.response.rag_used,
            citations: res.response.citations,
            answerGrounded: res.response.answer_grounded,
          },
        };
        setMessages((prev) => [...prev, assistantMsg]);
        fetchSessions();
      } else {
        const errorMsg: Message = {
          id: crypto.randomUUID(),
          role: "error",
          content: res.error || "An error occurred",
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } catch (err: any) {
      toast.error(err.message || "Network error");
    }
    setThinking(false);
  };

  if (showModal) {
    return <DocUploadModal onReady={() => setShowModal(false)} showBack />;
  }

  const sidebarSessions = sessions.map((s) => ({ id: s.chat_id, title: s.title, updated_at: s.updated_at }));

  // Derive citations from latest assistant message
  const latestAssistant = [...messages].reverse().find((m) => m.role === "assistant");
  const latestCitations = latestAssistant?.metadata?.citations || [];
  const hasCitations = latestCitations.length > 0;

  return (
    <div className="flex flex-col h-screen bg-background">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        {/* Sidebar — 240px */}
        <div className="w-[240px] shrink-0">
          <Sidebar
            sessions={sidebarSessions}
            activeId={chatId}
            onSelect={handleSelectSession}
            onDelete={handleDeleteSession}
            onNewChat={handleNewChat}
            loading={sessionsLoading}
          />
        </div>

        {/* Chat — flex-1 */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* Top bar */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-background">
            <h2 className="font-mono italic uppercase text-[11px] tracking-[0.12em] font-bold text-foreground truncate">
              {sessions.find((s) => s.chat_id === chatId)?.title || "New Chat"}
            </h2>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-[4px] bg-card border border-border font-mono uppercase text-[10px] tracking-[0.1em] text-foreground hover:bg-muted transition-all duration-200"
            >
              Manage Docs
            </button>
          </div>

          {/* Chat area */}
          <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4 relative" ref={chatContainerRef}>
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full gap-4">
                <span className="font-mono italic font-bold text-[80px] leading-none text-card">DM</span>
                {/* Decorative prompt chips */}
                <div className="flex flex-wrap justify-center gap-2 mt-4">
                  <div className="px-3 py-1.5 bg-card border border-border rounded-[4px] font-mono uppercase text-[10px] tracking-[0.1em] text-muted-foreground">
                    "Summarize the Q4 report"
                  </div>
                  <div className="px-3 py-1.5 bg-card border border-border rounded-[4px] font-mono uppercase text-[10px] tracking-[0.1em] text-muted-foreground">
                    "Find clauses about liability"
                  </div>
                  <div className="px-3 py-1.5 bg-card border border-border rounded-[4px] font-mono uppercase text-[10px] tracking-[0.1em] text-muted-foreground">
                    "Compare revenue across docs"
                  </div>
                </div>
              </div>
            )}
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {thinking && <ThinkingIndicator />}
            <div ref={chatEndRef} />

            {/* Scroll to bottom button */}
            {showScrollBtn && (
              <button
                onClick={scrollToBottom}
                className="fixed bottom-20 right-[300px] w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-lg transition-all duration-200 hover:scale-110 z-10"
              >
                <ChevronDown size={16} />
              </button>
            )}
          </div>

          <ChatInput onSend={handleSend} placeholder="Ask a question about your documents..." disabled={thinking} />
        </div>

        {/* Citations panel — 280px, slides in from right */}
        <div
          className={`w-[280px] shrink-0 border-l border-border bg-card overflow-y-auto scrollbar-thin transition-transform duration-300 ${
            hasCitations ? "translate-x-0" : "translate-x-full"
          }`}
          style={{ marginRight: hasCitations ? 0 : -280 }}
        >
          <div className="p-4">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="font-mono italic font-bold uppercase text-[11px] tracking-[0.15em] text-foreground">Sources</h3>
              <span className="px-1.5 py-0.5 bg-primary/20 text-primary font-mono font-bold text-[9px] rounded-[2px]">
                {latestCitations.length}
              </span>
            </div>
            {latestCitations.map((c, i) => (
              <div key={i} className="relative bg-muted rounded-[4px] px-3 py-2 mb-2">
                <span className="absolute top-1 right-2 font-mono text-[10px] text-muted-foreground">
                  {Math.round(c.confidence * 100)}%
                </span>
                <p className="font-mono text-[11px] text-primary truncate pr-8">{c.source}</p>
                <p className="font-mono text-[10px] text-muted-foreground">Page {c.page}</p>
                <div className="mt-1.5 w-full h-1 bg-muted-foreground/20 rounded-[2px] overflow-hidden">
                  <div className="h-full bg-primary rounded-[2px]" style={{ width: `${c.confidence * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Copilot;
