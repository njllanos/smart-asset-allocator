import React from "react";
import { Info } from "lucide-react";

interface HelpTooltipProps {
  content: React.ReactNode;
}

export function HelpTooltip({ content }: HelpTooltipProps) {
  return (
    <div className="group relative inline-flex items-center ml-2 align-middle z-10">
      <Info className="h-4 w-4 text-slate-400 hover:text-blue-500 cursor-help transition-colors" />
      
      {/* Tooltip Container */}
      <div className="absolute bottom-full left-1/2 mb-2 w-64 -translate-x-1/2 
                      invisible opacity-0 group-hover:visible group-hover:opacity-100 
                      transition-all duration-200 ease-in-out z-50">
        
        <div className="relative bg-slate-900 text-slate-50 text-xs rounded-lg py-2 px-3 shadow-xl border border-slate-700 leading-relaxed text-center">
          {content}
          
          {/* Flechita decorativa */}
          <div className="absolute top-full left-1/2 -mt-1 h-2 w-2 -translate-x-1/2 rotate-45 bg-slate-900 border-r border-b border-slate-700"></div>
        </div>
      </div>
    </div>
  );
}