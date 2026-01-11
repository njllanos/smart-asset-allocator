"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { TrendingUp, Shield, Target, Percent } from "lucide-react";
import { PortfolioMetrics } from "@/lib/api";

interface MetricsSummaryProps {
  metrics: PortfolioMetrics;
  portfolioValue: number;
}

export function MetricsSummary({ metrics, portfolioValue }:  MetricsSummaryProps) {
  const getSharpeRating = (sharpe: number) => {
    if (sharpe >= 2) return { label: "Excelente", color: "success" as const };
    if (sharpe >= 1) return { label: "Bueno", color: "default" as const };
    if (sharpe >= 0.5) return { label: "Aceptable", color: "secondary" as const };
    return { label: "Bajo", color: "destructive" as const };
  };

  const sharpeRating = getSharpeRating(metrics.sharpe_ratio);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Retorno Esperado</CardTitle>
          <TrendingUp className="h-4 w-4 text-green-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-700">{formatPercent(metrics.expected_annual_return)}</div>
          <p className="text-xs text-green-600">Aprox {formatCurrency(portfolioValue * (metrics.expected_annual_return / 100))} anual</p>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Volatilidad</CardTitle>
          <Shield className="h-4 w-4 text-blue-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-blue-700">{metrics.annual_volatility.toFixed(2)}%</div>
          <p className="text-xs text-blue-600">Riesgo anualizado</p>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Sharpe Ratio</CardTitle>
          <Target className="h-4 w-4 text-purple-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-purple-700">{metrics.sharpe_ratio.toFixed(3)}</div>
          <Badge variant={sharpeRating.color} className="mt-1">{sharpeRating.label}</Badge>
        </CardContent>
      </Card>

      <Card className="bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-950 dark:to-amber-900">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Valor del Portafolio</CardTitle>
          <Percent className="h-4 w-4 text-amber-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-amber-700">{formatCurrency(portfolioValue)}</div>
          <p className="text-xs text-amber-600">Capital inicial</p>
        </CardContent>
      </Card>
    </div>
  );
}
