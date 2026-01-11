"use client";

import React from "react";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

interface EfficientFrontierProps {
  frontierPoints: Array<{ return:  number; volatility: number; sharpe: number }>;
  currentPortfolio?:  { return: number; volatility: number };
}

export function EfficientFrontier({ frontierPoints, currentPortfolio }: EfficientFrontierProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Frontera Eficiente</CardTitle>
        <CardDescription>Relacion riesgo-retorno optima</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 20, right:  20, bottom: 20, left:  20 }}>
              <XAxis type="number" dataKey="volatility" name="Volatilidad" unit="%" domain={["auto", "auto"]} label={{ value: "Volatilidad (%)", position: "bottom" }} />
              <YAxis type="number" dataKey="return" name="Retorno" unit="%" domain={["auto", "auto"]} label={{ value: "Retorno (%)", angle: -90, position: "left" }} />
              <Tooltip formatter={(value:  number) => `${value.toFixed(2)}%`} />
              <Scatter name="Frontera Eficiente" data={frontierPoints} fill="#3b82f6" line={{ stroke: "#3b82f6", strokeWidth: 2 }} />
              {currentPortfolio && <Scatter name="Portafolio Actual" data={[currentPortfolio]} fill="#10b981" />}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
