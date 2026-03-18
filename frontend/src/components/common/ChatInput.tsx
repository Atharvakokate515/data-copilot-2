import React, { useState } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (text: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, placeholder = "Type a message...", disabled }) => {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 p-3 border-t border-border bg-card/50">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 bg-muted border border-border rounded-[4px] px-4 py-2.5 text-sm text-foreground font-mono uppercase placeholder:text-muted-foreground placeholder:uppercase placeholder:text-[11px] placeholder:tracking-[0.1em] focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all duration-200"
      />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="p-2.5 bg-primary text-primary-foreground rounded-[4px] hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 hover:shadow-lg hover:shadow-primary/25"
      >
        <Send size={18} />
      </button>
    </form>
  );
};

export default ChatInput;
