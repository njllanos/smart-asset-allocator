"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import { StressScenario } from "@/lib/api";
import { AlertTriangle } from "lucide-react";
// Importamos el tooltip
import { HelpTooltip } from "@/components/ui/help-tooltip";

interface StressScenariosProps {
  scenarios: StressScenario[];
  portfolioValue: number;
}

export function StressScenarios({ scenarios, portfolioValue }: StressScenariosProps) {
  const getSeverityColor = (impact: number) => {
    if (impact < -30) return "bg-red-500 text-white hover:bg-red-600";
    if (impact < -20) return "bg-orange-500 text-white hover:bg-orange-600";
    // CORRECCIÓN VISUAL: Texto oscuro sobre fondo amarillo para legibilidad
    return "bg-yellow-500 text-slate-900 hover:bg-yellow-600";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-yellow-500" />
          Escenarios de Estrés
          {/* TOOLTIP: Explicación de Stress Testing */}
          <HelpTooltip content="Pruebas de resistencia ('Stress Testing') que simulan cómo reaccionaría tu portafolio si se repitieran crisis históricas reales (como la Crisis Subprime de 2008 o el COVID-19). Ayuda a medir la fragilidad de tus inversiones frente a eventos de 'Cisne Negro'." />
        </CardTitle>
        <CardDescription>Impacto estimado bajo eventos de mercado históricos</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {scenarios.map((scenario) => (
            <div key={scenario.scenario_name} className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
              <div className="flex-1">
                <p className="font-medium">{scenario.description}</p>
                <p className="text-sm text-muted-foreground">
                  VaR bajo estrés: {formatCurrency(scenario.var_under_stress)}
                </p>
              </div>
              <div className="text-right">
                <Badge className={getSeverityColor(scenario.portfolio_impact_percent)}>
                  {scenario.portfolio_impact_percent.toFixed(1)}%
                </Badge>
                <p className="text-sm font-medium text-red-600 mt-1">
                  {formatCurrency(scenario.portfolio_impact_amount)}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}