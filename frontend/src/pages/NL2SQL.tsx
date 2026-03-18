import React, { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "sonner";
import Sidebar from "@/components/common/Sidebar";
import ChatMessage from "@/components/common/ChatMessage";
import ChatInput from "@/components/common/ChatInput";
import ThinkingIndicator from "@/components/common/ThinkingIndicator";
import DBConnectionModal from "@/components/nl2sql/DBConnectionModal";
import ResultsPanel from "@/components/nl2sql/ResultsPanel";
import Navbar from "@/components/common/Navbar";
import { chatDB, getNL2SQLSessions, getSessionHistory, deleteNL2SQLSession } from "@/api/client";
import type { Message, NL2SQLSession, ExecutionResult, ChartSuggestion, Plan } from "@/types";

const NL2SQL: React.FC = () => {
  const [dbUrl, setDbUrl] = useState("");
  const [dbName, setDbName] = useState("");
  const [connected, setConnected] = useState(false);
  const [showModal, setShowModal] = useState(true);

  const [sessionId, setSessionId] = useState<string>(crypto.randomUUID());
  const [sessions, setSessions] = useState<NL2SQLSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [thinking, setThinking] = useState(false);

  // Results panel state
  const [currentSql, setCurrentSql] = useState<string | null>(null);
  const [currentExecution, setCurrentExecution] = useState<ExecutionResult | null>(null);
  const [currentChart, setCurrentChart] = useState<ChartSuggestion | null>(null);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);

  const [dividerPos, setDividerPos] = useState(55);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const scrollToBottom = () => chatEndRef.current?.scrollIntoView({ behavior: "smooth" });

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await getNL2SQLSessions();
      setSessions(data);
    } catch { /* ignore */ }
    setSessionsLoading(false);
  }, []);

  useEffect(() => { if (connected) fetchSessions(); }, [connected, fetchSessions]);
  useEffect(scrollToBottom, [messages, thinking]);

  const handleConnected = (url: string, name: string, _tables: string[]) => {
    setDbUrl(url);
    setDbName(name);
    setConnected(true);
    setShowModal(false);
  };

  const handleNewChat = () => {
    setSessionId(crypto.randomUUID());
    setMessages([]);
    setCurrentSql(null);
    setCurrentExecution(null);
    setCurrentChart(null);
    setCurrentPlan(null);
  };

  const handleSelectSession = async (id: string | number) => {
    try {
      const data = await getSessionHistory(id as string);
      setSessionId(id as string);
      const restored: Message[] = data.chat_history.map((m: any, i: number) => ({
        id: `restored-${i}`,
        role: m.role === "user" ? "user" : "assistant",
        content: m.content,
      }));
      setMessages(restored);
      setCurrentSql(data.last_sql);
      setCurrentExecution(null);
      setCurrentChart(null);
      setCurrentPlan(null);
    } catch (err: any) {
      toast.error("Failed to load session");
    }
  };

  const handleDeleteSession = async (id: string | number) => {
    setSessions((prev) => prev.filter((s) => s.session_id !== id));
    try { await deleteNL2SQLSession(id as string); } catch { fetchSessions(); }
    if (sessionId === id) handleNewChat();
  };

  const handleSend = async (text: string, clarificationResponse?: string) => {
    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: text };
    if (!clarificationResponse) setMessages((prev) => [...prev, userMsg]);
    setThinking(true);

    try {
      const res = await chatDB(dbUrl, text, sessionId, clarificationResponse);

      if (res.success) {
        const assistantMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.summary || "Query executed successfully.",
          metadata: {
            sql: res.generated_sql,
            summary: res.summary,
            chart: res.chart_suggestion,
            execution: res.execution,
            plan: res.plan,
            wasRetried: res.was_retried,
          },
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setCurrentSql(res.generated_sql || null);
        setCurrentExecution(res.execution || null);
        setCurrentChart(res.chart_suggestion || null);
        setCurrentPlan(res.plan || null);
        fetchSessions();
      } else if (res.needs_clarification) {
        const clarifyMsg: Message = {
          id: crypto.randomUUID(),
          role: "clarification",
          content: res.question || "Could you clarify?",
          metadata: { question: res.question, originalInput: text },
        };
        setMessages((prev) => [...prev, clarifyMsg]);
      } else {
        const errorMsg: Message = {
          id: crypto.randomUUID(),
          role: "error",
          content: res.error || "An error occurred",
          metadata: { errorCode: res.error_code, sql: res.generated_sql },
        };
        setMessages((prev) => [...prev, errorMsg]);
        if (res.generated_sql) setCurrentSql(res.generated_sql);
      }
    } catch (err: any) {
      toast.error(err.message || "Network error");
    }
    setThinking(false);
  };

  const handleClarification = (originalInput: string) => (response: string) => {
    handleSend(originalInput, response);
  };

  const handleMouseDown = () => { dragging.current = true; };
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!dragging.current) return;
    const container = document.getElementById("nl2sql-main");
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const pct = ((e.clientY - rect.top) / rect.height) * 100;
    setDividerPos(Math.max(25, Math.min(75, pct)));
  }, []);
  const handleMouseUp = useCallback(() => { dragging.current = false; }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  if (showModal) {
    return <DBConnectionModal onConnected={handleConnected} showBack />;
  }

  const sidebarSessions = sessions.map((s) => ({ id: s.session_id, title: s.title, updated_at: s.updated_at }));

  return (
    <div className="flex flex-col h-screen bg-background">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar
          sessions={sidebarSessions}
          activeId={sessionId}
          onSelect={handleSelectSession}
          onDelete={handleDeleteSession}
          onNewChat={handleNewChat}
          loading={sessionsLoading}
        />

        <div className="flex flex-col flex-1 min-w-0">
          {/* Top bar */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-background">
            <h2 className="font-mono italic uppercase text-[11px] tracking-[0.12em] font-bold text-foreground truncate">
              {sessions.find((s) => s.session_id === sessionId)?.title || "New Chat"}
            </h2>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-3 py-1 rounded-[4px] bg-card border border-border font-mono uppercase text-[10px] tracking-[0.1em] text-foreground hover:bg-muted transition-all duration-200"
            >
              <span className="w-2 h-2 rounded-full bg-primary" />
              <span>CONNECTED TO {dbName}</span>
            </button>
          </div>

          {/* Main area */}
          <div id="nl2sql-main" className="flex-1 flex flex-col min-h-0">
            {/* Chat */}
            <div className="overflow-y-auto scrollbar-thin p-4 space-y-4" style={{ height: `${dividerPos}%` }}>
              {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full gap-2">
                  <span className="font-mono text-xl text-primary animate-blink-cursor">&gt;</span>
                  <span className="font-mono uppercase text-[11px] tracking-[0.15em] text-muted-foreground">
                    CONNECT A DATABASE AND START QUERYING
                  </span>
                </div>
              )}
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onClarificationSubmit={
                    msg.role === "clarification" ? handleClarification(msg.metadata?.originalInput || "") : undefined
                  }
                />
              ))}
              {thinking && <ThinkingIndicator />}
              <div ref={chatEndRef} />
            </div>

            <ChatInput onSend={(t) => handleSend(t)} placeholder="> ASK YOUR DATABASE ANYTHING..." disabled={thinking} />

            {/* Divider */}
            <div className="relative shrink-0">
              <div
                onMouseDown={handleMouseDown}
                className="h-1.5 bg-border hover:bg-primary/40 cursor-row-resize transition-all duration-200"
              />
              <span className="absolute left-1/2 -translate-x-1/2 -top-2.5 font-mono text-[9px] tracking-[0.1em] text-muted-foreground bg-background px-2">
                // EXECUTION LAYER
              </span>
            </div>

            {/* Results */}
            <div style={{ height: `${100 - dividerPos}%` }} className="min-h-0">
              <ResultsPanel sql={currentSql} execution={currentExecution} chart={currentChart} plan={currentPlan} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NL2SQL;
