"use client";

import React from "react";
import {
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Scatter
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
// Importamos el tooltip
import { HelpTooltip } from "@/components/ui/help-tooltip";

interface EfficientFrontierProps {
  frontierPoints: Array<{ return: number; volatility: number; sharpe: number }>;
  currentPortfolio?: { return: number; volatility: number };
}

// Tooltip Minimalista y Oscuro (Estilo Bloomberg)
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    // Detectar si el tooltip es sobre la curva o sobre el punto del usuario
    const data = payload[0].payload;
    const isPortfolio = data.name === "Tu Portafolio";

    return (
      <div className="bg-slate-900 text-white border border-slate-700 p-3 rounded-md shadow-2xl text-xs">
        <p className="font-bold mb-2 border-b border-slate-700 pb-1 text-slate-300">
          {isPortfolio ? "TU PORTAFOLIO SELECCIONADO" : "PUNTO DE FRONTERA"}
        </p>
        <div className="space-y-1 font-mono">
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Retorno Esp.:</span>
            <span className="text-emerald-400 font-bold">+{data.return?.toFixed(2)}%</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Riesgo (Vol):</span>
            <span className="text-amber-400 font-bold">{data.volatility?.toFixed(2)}%</span>
          </div>
          {data.sharpe && (
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Sharpe:</span>
              <span className="text-blue-400">{data.sharpe.toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>
    );
  }
  return null;
};

// Renderizado personalizado del punto del usuario (Bullseye / Mira telescópica)
const renderCustomizedActiveDot = (props: any) => {
  const { cx, cy } = props;
  return (
    <g>
      {/* Halo exterior suave */}
      <circle cx={cx} cy={cy} r={12} fill="rgba(16, 185, 129, 0.2)" />
      {/* Borde blanco para contraste */}
      <circle cx={cx} cy={cy} r={6} fill="#10b981" stroke="white" strokeWidth={2} />
      {/* Etiqueta flotante */}
      <text x={cx} y={cy - 20} textAnchor="middle" fill="#10b981" fontSize={11} fontWeight="bold">
        TÚ
      </text>
    </g>
  );
};

export function EfficientFrontier({ frontierPoints, currentPortfolio }: EfficientFrontierProps) {
  if (!frontierPoints || frontierPoints.length === 0) return null;

  // Aseguramos que los puntos estén ordenados por volatilidad para que la línea se dibuje bien
  const sortedPoints = [...frontierPoints].sort((a, b) => a.volatility - b.volatility);

  // Preparamos los datos del usuario para el Scatter superpuesto
  const userPointData = currentPortfolio ? [{
    ...currentPortfolio,
    name: "Tu Portafolio",
    sharpe: 0 // No relevante para visualización del punto
  }] : [];

  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
            <div>
                {/* AQUI AGREGAMOS EL TOOLTIP */}
                <CardTitle className="text-lg font-semibold text-slate-800 flex items-center">
                    Frontera Eficiente
                    <HelpTooltip content="Representación gráfica de la Teoría Moderna de Portafolios (Markowitz). La línea azul indica el retorno máximo posible para cada nivel de riesgo. Cualquier punto debajo de la línea es subóptimo." />
                </CardTitle>
                <CardDescription className="text-xs">
                Análisis Riesgo vs. Retorno
                </CardDescription>
            </div>
            {/* Leyenda simple manual */}
            <div className="flex gap-3 text-[10px] text-slate-500 font-medium">
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-blue-500/20 border border-blue-500 rounded-sm"></div>
                    <span>Mercado Eficiente</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full ring-1 ring-emerald-200"></div>
                    <span>Tu Selección</span>
                </div>
            </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[320px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart margin={{ top: 25, right: 20, bottom: 20, left: 0 }}>
              <defs>
                {/* Gradiente elegante bajo la curva */}
                <linearGradient id="colorFrontier" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              
              <XAxis 
                dataKey="volatility" 
                type="number" 
                domain={['auto', 'auto']}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}%`}
                label={{ value: 'Riesgo (Volatilidad Anual)', position: 'bottom', offset: 0, fontSize: 10, fill: '#94a3b8' }}
                style={{ fontSize: '10px', fill: '#64748b' }}
                allowDataOverflow={true} // Importante para que no corte puntos
              />
              
              <YAxis 
                dataKey="return" 
                type="number" 
                domain={['auto', 'auto']}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}%`}
                label={{ value: 'Retorno Esperado', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#94a3b8' }}
                style={{ fontSize: '10px', fill: '#64748b' }}
              />
              
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#94a3b8', strokeWidth: 1, strokeDasharray: '4 4' }} />

              {/* 1. LA CURVA (AREA + LINEA) */}
              <Area
                data={sortedPoints}
                type="monotone" // Esto suaviza la línea (crucial para estética)
                dataKey="return"
                stroke="#3b82f6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorFrontier)"
                activeDot={{ r: 4, strokeWidth: 0 }} // Desactivar punto gigante al pasar mouse sobre la línea
              />

              {/* 2. TU PORTAFOLIO (PUNTO DE PRECISIÓN) */}
              <Scatter 
                data={userPointData} 
                shape={renderCustomizedActiveDot}
                isAnimationActive={true}
              />

            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}