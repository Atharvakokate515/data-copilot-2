import React from "react";

interface TableDisplayProps {
  colNames: string[];
  rows: any[][];
}

const TableDisplay: React.FC<TableDisplayProps> = ({ colNames, rows }) => {
  if (!colNames.length) return <p className="font-mono text-sm text-muted-foreground p-4">No data returned.</p>;

  return (
    <div className="overflow-auto scrollbar-thin max-h-[400px]">
      <table className="w-full text-[11px] font-mono">
        <thead>
          <tr className="border-b border-border">
            {colNames.map((col) => (
              <th key={col} className="text-left px-3 py-2 uppercase text-[10px] tracking-[0.12em] text-muted-foreground font-bold whitespace-nowrap sticky top-0 bg-card">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border/50 hover:bg-card/60 transition-all duration-200">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-1.5 text-foreground whitespace-nowrap">
                  {cell === null ? <span className="text-muted-foreground italic">NULL</span> : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TableDisplay;
