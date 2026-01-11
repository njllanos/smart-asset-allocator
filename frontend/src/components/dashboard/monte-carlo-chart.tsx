"use client";

import React from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import { MonteCarloPath } from "@/lib/api";

interface MonteCarloChartProps {
  samplePaths: MonteCarloPath[];
  portfolioValue: number;
}

export function MonteCarloChart({ samplePaths, portfolioValue }: MonteCarloChartProps) {
  const chartData = samplePaths[0]?.values.map((_, index) => {
    const point:  Record<string, number> = { day: index * 5 };
    samplePaths.forEach((path) => {
      point[path. percentile] = path.values[index];
    });
    return point;
  }) || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Simulacion Monte Carlo</CardTitle>
        <CardDescription>Proyeccion a 1 año con bandas de confianza</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorP95" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorP5" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="day" tickFormatter={(v) => `Dia ${v}`} />
              <YAxis tickFormatter={(v) => formatCurrency(v)} domain={["auto", "auto"]} />
              <Tooltip
                formatter={(value:  number) => formatCurrency(value)}
                labelFormatter={(label) => `Dia ${label}`}
              />
              <Legend />
              <Area type="monotone" dataKey="p95" name="Percentil 95" stroke="#10b981" fill="url(#colorP95)" strokeWidth={2} />
              <Area type="monotone" dataKey="p75" name="Percentil 75" stroke="#3b82f6" fill="transparent" strokeWidth={1} strokeDasharray="5 5" />
              <Area type="monotone" dataKey="median" name="Mediana" stroke="#f59e0b" fill="transparent" strokeWidth={2} />
              <Area type="monotone" dataKey="p25" name="Percentil 25" stroke="#8b5cf6" fill="transparent" strokeWidth={1} strokeDasharray="5 5" />
              <Area type="monotone" dataKey="p5" name="Percentil 5" stroke="#ef4444" fill="url(#colorP5)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
