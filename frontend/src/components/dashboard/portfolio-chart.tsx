"use client";

import React, { useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Sector } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { PortfolioAllocation } from "@/lib/api";

interface PortfolioChartProps {
  allocations: PortfolioAllocation[];
}

// Colores Institucionales (Azules, Violetas, Esmeraldas - No arcoiris)
const COLORS = [
  "#3b82f6", // Blue 500
  "#8b5cf6", // Violet 500
  "#10b981", // Emerald 500
  "#f59e0b", // Amber 500
  "#06b6d4", // Cyan 500
  "#ec4899", // Pink 500
  "#6366f1", // Indigo 500
  "#84cc16", // Lime 500
];

// Renderizado activo (efecto "pop" al pasar el mouse)
const renderActiveShape = (props: any) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, payload, percent, value } = props;

  return (
    <g>
      <text x={cx} y={cy} dy={-10} textAnchor="middle" fill="#1e293b" className="text-lg font-bold">
        {payload.ticker}
      </text>
      <text x={cx} y={cy} dy={15} textAnchor="middle" fill="#64748b" className="text-sm">
        {`${(percent * 100).toFixed(1)}%`}
      </text>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 6} // Se expande un poco
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
      />
      <Sector
        cx={cx}
        cy={cy}
        startAngle={startAngle}
        endAngle={endAngle}
        innerRadius={outerRadius + 8}
        outerRadius={outerRadius + 12}
        fill={fill}
        fillOpacity={0.3} // Halo externo
      />
    </g>
  );
};

export function PortfolioChart({ allocations }: PortfolioChartProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  const onPieEnter = (_: any, index: number) => {
    setActiveIndex(index);
  };

  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg font-semibold text-slate-800">Distribución de Activos</CardTitle>
        <CardDescription className="text-xs">Pesos óptimos sugeridos</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col md:flex-row items-center h-[300px]">
          {/* Gráfico Donut */}
          <div className="h-full w-full md:w-1/2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  activeIndex={activeIndex}
                  activeShape={renderActiveShape}
                  data={allocations}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={2}
                  dataKey="weight"
                  onMouseEnter={onPieEnter}
                >
                  {allocations.map((entry, index) => (
                    <Cell 
                        key={`cell-${index}`} 
                        fill={COLORS[index % COLORS.length]} 
                        stroke="rgba(255,255,255,0.5)"
                        strokeWidth={1}
                    />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Leyenda / Tabla Lateral */}
          <div className="w-full md:w-1/2 pl-0 md:pl-6 space-y-3 overflow-y-auto max-h-[250px] pr-2 custom-scrollbar">
            {allocations.map((alloc, index) => (
              <div 
                key={alloc.ticker} 
                className={`flex items-center justify-between p-2 rounded-lg transition-colors cursor-pointer ${index === activeIndex ? "bg-slate-100 ring-1 ring-slate-200" : "hover:bg-slate-50"}`}
                onMouseEnter={() => setActiveIndex(index)}
              >
                <div className="flex items-center gap-3">
                  <div 
                    className="w-3 h-3 rounded-full shadow-sm" 
                    style={{ backgroundColor: COLORS[index % COLORS.length] }} 
                  />
                  <span className="font-medium text-sm text-slate-700">{alloc.ticker}</span>
                </div>
                <div className="text-right">
                    <span className="block font-bold text-sm text-slate-900">{alloc.weight_percent.toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}