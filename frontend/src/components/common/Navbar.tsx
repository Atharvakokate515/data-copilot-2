import { NavLink } from "react-router-dom";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `font-mono uppercase text-[11px] tracking-[0.15em] px-3 py-1 border-b-2 transition-all duration-200 ${
    isActive
      ? "text-primary border-primary"
      : "text-muted-foreground border-transparent hover:text-foreground"
  }`;

const Navbar = () => (
  <nav className="flex items-center justify-between h-12 px-4 border-b border-border bg-background shrink-0">
    <NavLink to="/" className="flex items-center gap-0 no-underline">
      <span className="font-mono italic font-bold text-lg tracking-[0.15em] text-foreground">DATA</span>
      <span className="font-mono italic font-bold text-lg tracking-[0.15em] text-primary">MIND</span>
    </NavLink>

    <div className="flex items-center gap-1">
      <NavLink to="/" end className={navLinkClass}>HOME</NavLink>
      <NavLink to="/nl2sql" className={navLinkClass}>NL2SQL</NavLink>
      <NavLink to="/copilot" className={navLinkClass}>COPILOT</NavLink>
    </div>

    <div className="flex items-center gap-2">
      <span className="w-2 h-2 rounded-full bg-primary" style={{ animation: "pulse-dot 2s ease-in-out infinite" }} />
      <span className="font-mono uppercase text-[9px] tracking-[0.15em] text-muted-foreground">SYSTEM ONLINE</span>
    </div>
  </nav>
);

export default Navbar;
