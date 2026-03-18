import React, { useState } from "react";
import { ArrowLeft, Database, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Modal from "@/components/common/Modal";
import { testConnection } from "@/api/client";

interface DBConnectionModalProps {
  onConnected: (dbUrl: string, dbName: string, tables: string[]) => void;
  onClose?: () => void;
  showBack?: boolean;
}

const DBConnectionModal: React.FC<DBConnectionModalProps> = ({ onConnected, onClose, showBack = true }) => {
  const navigate = useNavigate();
  const [host, setHost] = useState("localhost");
  const [port, setPort] = useState("5432");
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("postgres");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const dbUrl = `postgresql://${username}:${password}@${host}:${port}/${database}`;
    setLoading(true);
    try {
      const res = await testConnection(dbUrl);
      if (res.success) {
        onConnected(dbUrl, res.db_name, res.tables);
      } else {
        setError(res.error || "Connection failed");
      }
    } catch (err: any) {
      setError(err.message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  const inputClass = "w-full bg-muted border border-border rounded-[4px] px-3 py-2.5 text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all duration-200";

  return (
    <Modal title="Connect to Database" onClose={onClose}>
      {showBack && (
        <button onClick={() => navigate("/")} className="flex items-center gap-1 font-mono uppercase text-[10px] tracking-[0.15em] text-muted-foreground hover:text-foreground mb-4 transition-all duration-200">
          <ArrowLeft size={14} /> Back to home
        </button>
      )}
      <form onSubmit={handleConnect} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="font-mono uppercase text-[10px] tracking-[0.15em] text-muted-foreground mb-1 block">Host</label>
            <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" className={inputClass} />
          </div>
          <div>
            <label className="font-mono uppercase text-[10px] tracking-[0.15em] text-muted-foreground mb-1 block">Port</label>
            <input value={port} onChange={(e) => setPort(e.target.value)} placeholder="5432" className={inputClass} />
          </div>
        </div>
        <div>
          <label className="font-mono uppercase text-[10px] tracking-[0.15em] text-muted-foreground mb-1 block">Database</label>
          <input value={database} onChange={(e) => setDatabase(e.target.value)} placeholder="mydb" className={inputClass} />
        </div>
        <div>
          <label className="font-mono uppercase text-[10px] tracking-[0.15em] text-muted-foreground mb-1 block">Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="postgres" className={inputClass} />
        </div>
        <div>
          <label className="font-mono uppercase text-[10px] tracking-[0.15em] text-muted-foreground mb-1 block">Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} />
        </div>
        {error && <p className="text-sm font-mono text-destructive bg-destructive/10 rounded-[4px] px-3 py-2">{error}</p>}
        <button
          type="submit"
          disabled={loading || !database}
          className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-[4px] py-2.5 font-mono uppercase text-[11px] tracking-[0.12em] font-bold hover:bg-primary/90 disabled:opacity-50 transition-all duration-200"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Database size={16} />}
          {loading ? "CONNECTING..." : "CONNECT"}
        </button>
      </form>
    </Modal>
  );
};

export default DBConnectionModal;
