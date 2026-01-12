"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { TrendingUp, Activity, Crosshair, Wallet } from "lucide-react"; // Iconos más profesionales
import { PortfolioMetrics } from "@/lib/api";

interface MetricsSummaryProps {
  metrics: PortfolioMetrics;
  portfolioValue: number;
}

export function MetricsSummary({ metrics, portfolioValue }: MetricsSummaryProps) {
  // Cálculo de ganancia estimada en dinero
  const estimatedGain = portfolioValue * (metrics.expected_annual_return / 100);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {/* 1. RETORNO (Verde) */}
      <Card className="border-l-4 border-l-emerald-500 shadow-sm">
        <CardContent className="p-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Retorno Esperado</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-2">
                {formatPercent(metrics.expected_annual_return)}
              </h3>
              <p className="text-xs text-emerald-600 mt-1 font-medium">
                +{formatCurrency(estimatedGain)} / año
              </p>
            </div>
            <div className="p-2 bg-emerald-100 rounded-lg">
              <TrendingUp className="h-5 w-5 text-emerald-600" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2. VOLATILIDAD (Naranja - Riesgo) */}
      <Card className="border-l-4 border-l-orange-500 shadow-sm">
        <CardContent className="p-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Volatilidad (Riesgo)</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-2">
                {metrics.annual_volatility.toFixed(2)}%
              </h3>
              <p className="text-xs text-orange-600 mt-1 font-medium">
                Desviación Anual
              </p>
            </div>
            <div className="p-2 bg-orange-100 rounded-lg">
              <Activity className="h-5 w-5 text-orange-600" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 3. SHARPE RATIO (Azul - Calidad) */}
      <Card className="border-l-4 border-l-blue-500 shadow-sm">
        <CardContent className="p-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Sharpe Ratio</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-2">
                {metrics.sharpe_ratio.toFixed(2)}
              </h3>
              <p className="text-xs text-blue-600 mt-1 font-medium">
                Eficiencia Riesgo/Retorno
              </p>
            </div>
            <div className="p-2 bg-blue-100 rounded-lg">
              <Crosshair className="h-5 w-5 text-blue-600" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 4. VALOR PORTAFOLIO (Gris - Capital) */}
      <Card className="border-l-4 border-l-slate-500 shadow-sm">
        <CardContent className="p-6">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Capital Total</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-2">
                {formatCurrency(portfolioValue)}
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Monto Invertido
              </p>
            </div>
            <div className="p-2 bg-slate-100 rounded-lg">
              <Wallet className="h-5 w-5 text-slate-600" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}