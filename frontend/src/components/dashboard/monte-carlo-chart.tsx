"use client";

import React from "react";
import {
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  Line,
  ComposedChart
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { MonteCarloPath } from "@/lib/api";
// Importamos el tooltip
import { HelpTooltip } from "@/components/ui/help-tooltip";

const formatCurrencyCompact = (value: number) => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    // FILTRO CLAVE: Eliminamos la entrada del Área de fondo para que no salga "Rango (p95)" duplicado
    const filteredPayload = payload.filter((entry: any) => entry.name !== "Rango de Confianza");

    return (
      <div className="bg-slate-900 text-white border border-slate-700 p-3 rounded-lg shadow-xl text-xs">
        <p className="font-bold mb-2 border-b border-slate-700 pb-1 text-slate-300">
          Día {label}
        </p>
        <div className="space-y-1 font-mono">
          {filteredPayload.sort((a: any, b: any) => b.value - a.value).map((entry: any, index: number) => (
            <div key={index} className="flex justify-between gap-4">
              <span style={{ color: entry.color }}>{entry.name}:</span>
              <span className="font-bold">
                {new Intl.NumberFormat("en-US", {
                  style: "currency",
                  currency: "USD",
                  maximumFractionDigits: 0,
                }).format(entry.value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

interface MonteCarloChartProps {
  samplePaths: MonteCarloPath[];
  portfolioValue: number;
}

export function MonteCarloChart({ samplePaths, portfolioValue }: MonteCarloChartProps) {
  if (!samplePaths || samplePaths.length < 3) return null;

  // Ordenamos los caminos por valor final para asegurar consistencia
  const sortedPaths = [...samplePaths].sort((a, b) => {
    const lastValueA = a.values[a.values.length - 1];
    const lastValueB = b.values[b.values.length - 1];
    return lastValueA - lastValueB;
  });

  const pessimisticPath = sortedPaths[0];            
  const medianPath = sortedPaths[Math.floor(sortedPaths.length / 2)]; 
  const optimisticPath = sortedPaths[sortedPaths.length - 1]; 

  const chartData = medianPath.values.map((_, index) => ({
    day: index,
    p5: pessimisticPath.values[index],
    median: medianPath.values[index],
    p95: optimisticPath.values[index],
  }));

  return (
    <Card className="border-slate-200 shadow-sm col-span-1 lg:col-span-2">
      <CardHeader>
        {/* TITULO CON TOOLTIP */}
        <CardTitle className="text-lg font-semibold text-slate-800 flex items-center">
            Proyección de Valor (Monte Carlo)
            <HelpTooltip content="Simulación de 5,000 futuros posibles usando Movimiento Browniano Geométrico. Genera caminos aleatorios basados en la media y volatilidad histórica para estimar rangos de probabilidad." />
        </CardTitle>
        <CardDescription className="text-xs">
          Rango de probabilidad al 90% de confianza.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <defs>
                {/* COLOR NEUTRO (Slate/Gris Azulado) */}
                <linearGradient id="colorUncertainty" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#64748b" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#64748b" stopOpacity={0} />
                </linearGradient>
              </defs>
              
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              
              <XAxis 
                dataKey="day" 
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `D${val}`}
                minTickGap={30}
                style={{ fontSize: '10px', fill: '#64748b' }}
              />
              
              <YAxis 
                domain={['auto', 'auto']}
                tickFormatter={formatCurrencyCompact}
                tickLine={false}
                axisLine={false}
                width={60}
                style={{ fontSize: '10px', fill: '#64748b' }}
              />
              
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} iconType="circle" />

              <ReferenceLine 
                y={portfolioValue} 
                stroke="#9ca3af" 
                strokeDasharray="3 3" 
                label={{ value: "Inicio", fontSize: 10, fill: "#9ca3af", position: "insideLeft" }} 
              />

              {/* 1. Área de Fondo (Rango de Confianza) */}
              <Area
                type="monotone"
                dataKey="p95"
                name="Rango de Confianza"
                stroke="none"
                fill="url(#colorUncertainty)"
                isAnimationActive={true}
                legendType="none"
              />

              {/* 2. Línea Superior (Optimista - Verde) */}
              <Line
                type="monotone"
                dataKey="p95"
                name="Optimista (95%)"
                stroke="#10b981" 
                strokeWidth={2}
                dot={false}
                strokeDasharray="4 4"
              />

              {/* 3. Línea Central (Mediana - Azul Vibrante) */}
              <Line
                type="monotone"
                dataKey="median"
                name="Esperado (Mediana)"
                stroke="#3b82f6" 
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 6, strokeWidth: 0 }}
              />

              {/* 4. Línea Inferior (Pesimista - Rojo Opaco) */}
              <Line
                type="monotone"
                dataKey="p5"
                name="Pesimista (5%)"
                stroke="#ef4444" 
                strokeWidth={2}
                dot={false}
                strokeDasharray="4 4"
              />

            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}