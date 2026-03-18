import { useNavigate } from "react-router-dom";
import { Database, Brain, ChevronDown } from "lucide-react";
import { useEffect, useRef } from "react";
import Navbar from "@/components/common/Navbar";

const Home = () => {
  const navigate = useNavigate();
  const featureRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("animate-fade-up");
            entry.target.classList.remove("opacity-0", "translate-y-[30px]");
          }
        });
      },
      { threshold: 0.1 }
    );
    const cards = featureRef.current?.querySelectorAll(".feature-card");
    cards?.forEach((card) => observer.observe(card));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero */}
      <div className="flex flex-col items-center justify-center px-4" style={{ minHeight: "calc(100vh - 48px)" }}>
        <h1 className="font-mono italic font-bold text-[48px] md:text-[96px] leading-none tracking-tight text-center mb-4">
          <span className="text-foreground">DATA</span>
          <span className="text-primary">MIND</span>
        </h1>
        <p className="font-mono uppercase text-[13px] tracking-[0.18em] text-muted-foreground text-center mb-16">
          Query your database. Search your documents. Get answers.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {/* NL2SQL Button */}
          <button
            onClick={() => navigate("/nl2sql")}
            className="group relative w-full md:w-[280px] h-[120px] bg-card border border-muted-foreground/30 rounded-[4px] p-6 text-left transition-all duration-200 hover:border-primary hover:shadow-[0_0_24px_rgba(172,190,87,0.2)]"
          >
            {/* L-bracket corners */}
            <span className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-primary" />
            <span className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-primary" />
            <span className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-primary" />
            <span className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-primary" />

            <div className="w-10 h-10 rounded-[4px] bg-primary/10 flex items-center justify-center mb-3">
              <Database size={20} className="text-primary" />
            </div>
            <h2 className="font-mono italic font-bold uppercase text-sm tracking-[0.12em] text-foreground mb-1">NL2SQL Pipeline</h2>
            <p className="font-mono text-[11px] text-muted-foreground">
              Connect to PostgreSQL and query with natural language
            </p>
            {/* Bottom line animation */}
            <span className="absolute bottom-0 left-0 h-[2px] bg-primary transition-all duration-300 w-0 group-hover:w-full" />
          </button>

          {/* Copilot Button */}
          <button
            onClick={() => navigate("/copilot")}
            className="group relative w-full md:w-[280px] h-[120px] bg-card border border-muted-foreground/30 rounded-[4px] p-6 text-left transition-all duration-200 hover:border-primary hover:shadow-[0_0_24px_rgba(172,190,87,0.2)]"
          >
            <span className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-primary" />
            <span className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-primary" />
            <span className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-primary" />
            <span className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-primary" />

            <div className="w-10 h-10 rounded-[4px] bg-primary/10 flex items-center justify-center mb-3">
              <Brain size={20} className="text-primary" />
            </div>
            <h2 className="font-mono italic font-bold uppercase text-sm tracking-[0.12em] text-foreground mb-1">RAG Copilot</h2>
            <p className="font-mono text-[11px] text-muted-foreground">
              Upload documents and ask questions across your knowledge base
            </p>
            <span className="absolute bottom-0 left-0 h-[2px] bg-primary transition-all duration-300 w-0 group-hover:w-full" />
          </button>
        </div>

        {/* Bouncing arrow */}
        <div className="mt-16 animate-bounce-arrow">
          <ChevronDown size={24} className="text-muted-foreground" />
        </div>
      </div>

      {/* Feature sections */}
      <div ref={featureRef} className="max-w-4xl mx-auto px-4 py-24 space-y-16">
        <div className="text-center mb-12">
          <h2 className="font-mono italic font-bold text-[32px] md:text-[64px] tracking-tight text-foreground uppercase">
            Features
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { title: "Natural Language SQL", desc: "Transform questions into optimized SQL queries automatically" },
            { title: "RAG Pipeline", desc: "Upload documents and get AI-powered answers with citations" },
            { title: "Smart Charts", desc: "Auto-generated visualizations from your query results" },
          ].map((f, i) => (
            <div
              key={i}
              className="feature-card opacity-0 translate-y-[30px] bg-card border border-border rounded-[4px] p-6 transition-all duration-200 hover:scale-[1.03] hover:border-primary hover:shadow-[0_0_24px_rgba(172,190,87,0.15)]"
            >
              <h3 className="font-mono italic font-bold uppercase text-xs tracking-[0.12em] text-foreground mb-2">{f.title}</h3>
              <p className="font-mono text-[11px] text-muted-foreground leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Home;
