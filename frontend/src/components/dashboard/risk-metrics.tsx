"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import { AlertTriangle, TrendingDown, Activity, BarChart3 } from "lucide-react";
import { VaRResult } from "@/lib/api";

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
  const var95 = metrics.var_results. find((v) => v.confidence_level === 0.95);

  return (
    <div className="grid grid-cols-1 md: grid-cols-2 lg:grid-cols-4 gap-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">VaR 95%</CardTitle>
          <AlertTriangle className="h-4 w-4 text-yellow-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-yellow-600">{formatCurrency(var95?. var_amount || 0)}</div>
          <p className="text-xs text-muted-foreground">{var95?.var_percent. toFixed(2)}% del portafolio</p>
          <p className="text-xs text-muted-foreground mt-1">ES: {formatCurrency(var95?.expected_shortfall || 0)}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Volatilidad Anual</CardTitle>
          <Activity className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-blue-600">{metrics.annual_volatility.toFixed(2)}%</div>
          <p className="text-xs text-muted-foreground">Desviacion estandar anualizada</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Max Drawdown</CardTitle>
          <TrendingDown className="h-4 w-4 text-red-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">{metrics.max_drawdown.toFixed(2)}%</div>
          <p className="text-xs text-muted-foreground">Mayor caida historica</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Prob.  Perdida &gt;10%</CardTitle>
          <BarChart3 className="h-4 w-4 text-purple-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-purple-600">{(metrics.prob_loss_10_percent * 100).toFixed(2)}%</div>
          <p className="text-xs text-muted-foreground">Probabilidad historica diaria</p>
          <div className="mt-2 flex gap-2">
            <Badge variant={metrics.kurtosis > 3 ? "warning" : "secondary"}>Kurtosis:  {metrics.kurtosis.toFixed(2)}</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
