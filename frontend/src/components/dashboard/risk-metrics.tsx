"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import { AlertTriangle, TrendingDown, Activity, BarChart3 } from "lucide-react";
import { VaRResult } from "@/lib/api";
// Importamos el tooltip
import { HelpTooltip } from "@/components/ui/help-tooltip";

interface RiskMetricsProps {
  metrics: {
    annual_volatility: number;
    max_drawdown: number;
    var_results: VaRResult[];
    skewness: number;
    kurtosis: number;
    prob_loss_10_percent: number;
  };
  portfolioValue: number;
}

export function RiskMetrics({ metrics, portfolioValue }: RiskMetricsProps) {
  const var95 = metrics.var_results.find((v) => v.confidence_level === 0.95);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. VaR 95% */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium flex items-center">
            VaR 95%
            <HelpTooltip content="Value at Risk (Valor en Riesgo). Estima la pérdida máxima esperada en un periodo dado con un 95% de confianza. Es decir, hay un 5% de probabilidad de perder más de esta cantidad." />
          </CardTitle>
          <AlertTriangle className="h-4 w-4 text-yellow-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-yellow-600">
            {formatCurrency(var95?.var_amount || 0)}
          </div>
          <p className="text-xs text-muted-foreground">
            {var95?.var_percent.toFixed(2)}% del portafolio
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            ES: {formatCurrency(var95?.expected_shortfall || 0)}
          </p>
        </CardContent>
      </Card>

      {/* 2. Volatilidad Anual */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium flex items-center">
            Volatilidad Anual
            <HelpTooltip content="Medida estadística de la dispersión de los retornos. Una volatilidad alta implica que el precio del activo oscila violentamente, lo que representa mayor riesgo e incertidumbre." />
          </CardTitle>
          <Activity className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-blue-600">
            {metrics.annual_volatility.toFixed(2)}%
          </div>
          <p className="text-xs text-muted-foreground">
            Desviación estándar anualizada
          </p>
        </CardContent>
      </Card>

      {/* 3. Max Drawdown */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium flex items-center">
            Max Drawdown
            <HelpTooltip content="La peor caída histórica registrada desde un pico hasta un fondo. Indica el dolor máximo (pérdida porcentual) que un inversor habría sufrido si hubiera comprado en el punto más alto y vendido en el más bajo." />
          </CardTitle>
          <TrendingDown className="h-4 w-4 text-red-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">
            {metrics.max_drawdown.toFixed(2)}%
          </div>
          <p className="text-xs text-muted-foreground">Mayor caída histórica</p>
        </CardContent>
      </Card>

      {/* 4. Probabilidad de Pérdida Extrema */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium flex items-center">
            Prob. Pérdida {'>'}10%
            <HelpTooltip content="Probabilidad de caída extrema en un solo día. La 'Kurtosis' mide el riesgo de sorpresas: un valor alto (>3.0) indica 'Colas Gordas', lo que significa que el portafolio es propenso a movimientos violentos e inesperados (Cisnes Negros) con mucha más frecuencia que un mercado normal." />
          </CardTitle>
          <BarChart3 className="h-4 w-4 text-purple-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-purple-600">
            {(metrics.prob_loss_10_percent * 100).toFixed(2)}%
          </div>
          <p className="text-xs text-muted-foreground">
            Probabilidad histórica diaria
          </p>
          <div className="mt-2 flex gap-2">
            <Badge variant={metrics.kurtosis > 3 ? "destructive" : "secondary"}>
              Kurtosis: {metrics.kurtosis.toFixed(2)}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
