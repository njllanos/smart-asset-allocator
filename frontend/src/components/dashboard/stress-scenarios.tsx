"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import { StressScenario } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

interface StressScenariosProps {
  scenarios: StressScenario[];
  portfolioValue: number;
}

export function StressScenarios({ scenarios, portfolioValue }: StressScenariosProps) {
  const getSeverityColor = (impact: number) => {
    if (impact < -30) return "bg-red-500";
    if (impact < -20) return "bg-orange-500";
    return "bg-yellow-500";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-yellow-500" />
          Escenarios de Estres
        </CardTitle>
        <CardDescription>Impacto estimado bajo eventos de mercado historicos</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {scenarios.map((scenario) => (
            <div key={scenario.scenario_name} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
              <div className="flex-1">
                <p className="font-medium">{scenario.description}</p>
                <p className="text-sm text-muted-foreground">VaR bajo estres: {formatCurrency(scenario.var_under_stress)}</p>
              </div>
              <div className="text-right">
                <Badge className={getSeverityColor(scenario.portfolio_impact_percent)}>
                  {scenario. portfolio_impact_percent.toFixed(1)}%
                </Badge>
                <p className="text-sm font-medium text-red-600 mt-1">{formatCurrency(scenario.portfolio_impact_amount)}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
