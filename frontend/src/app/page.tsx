"use client";

import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { TickerInput } from "@/components/dashboard/ticker-input";
import { PortfolioChart } from "@/components/dashboard/portfolio-chart";
import { MonteCarloChart } from "@/components/dashboard/monte-carlo-chart";
import { RiskMetrics } from "@/components/dashboard/risk-metrics";
import { SentimentCard } from "@/components/dashboard/sentiment-card";
import { StressScenarios } from "@/components/dashboard/stress-scenarios";
import { EfficientFrontier } from "@/components/dashboard/efficient-frontier";
import { MetricsSummary } from "@/components/dashboard/metrics-summary";
import {
  optimizationApi,
  riskApi,
  sentimentApi,
  OptimizationResponse,
  RiskAnalysisResponse,
  SentimentResponse,
} from "@/lib/api";
import {
  Loader2,
  PlayCircle,
  TrendingUp,
  Brain,
  BarChart3,
  RefreshCw,
} from "lucide-react";

type AnalysisStep = "idle" | "sentiment" | "optimization" | "risk" | "complete" | "error";

export default function Home() {
  const [tickers, setTickers] = useState<string[]>(["AAPL", "GOOGL", "MSFT", "AMZN"]);
  const [portfolioValue, setPortfolioValue] = useState(100000);
  const [objective, setObjective] = useState("max_sharpe");
  const [useSentiment, setUseSentiment] = useState(true);

  const [step, setStep] = useState<AnalysisStep>("idle");
  const [error, setError] = useState<string | null>(null);

  const [sentimentData, setSentimentData] = useState<SentimentResponse | null>(null);
  const [optimizationData, setOptimizationData] = useState<OptimizationResponse | null>(null);
  const [riskData, setRiskData] = useState<RiskAnalysisResponse | null>(null);

  const runAnalysis = async () => {
    if (tickers.length < 2) {
      setError("Necesitas al menos 2 tickers");
      return;
    }

    setError(null);
    setSentimentData(null);
    setOptimizationData(null);
    setRiskData(null);

    try {
      if (useSentiment) {
        setStep("sentiment");
        const sentiment = await sentimentApi.analyzeSentiment(tickers);
        setSentimentData(sentiment);
      }

      setStep("optimization");
      const optimization = await optimizationApi.optimize(tickers, objective, useSentiment);
      setOptimizationData(optimization);

      setStep("risk");
      const risk = await riskApi. analyzeRisk(tickers, optimization. weights, portfolioValue);
      setRiskData(risk);

      setStep("complete");
    } catch (err:  unknown) {
      setStep("error");
      const errorObj = err as { response?: { data?: { detail?: { message?: string } } }; message?: string };
      setError(errorObj.response?.data?.detail?.message || errorObj.message || "Error en el analisis");
    }
  };

  const isLoading = step !== "idle" && step !== "complete" && step !== "error";

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold">Smart Asset Allocator</h1>
                <p className="text-sm text-muted-foreground">Optimizacion de portafolios con IA</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="gap-1">
                <Brain className="h-3 w-3" /> FinBERT
              </Badge>
              <Badge variant="outline" className="gap-1">
                <BarChart3 className="h-3 w-3" /> Black-Litterman
              </Badge>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Configuracion del Analisis</CardTitle>
            <CardDescription>Selecciona los activos y parametros para optimizar tu portafolio</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <label className="text-sm font-medium mb-2 block">Activos</label>
              <TickerInput tickers={tickers} onTickersChange={setTickers} maxTickers={10} />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Valor del Portafolio</label>
                <Input
                  type="number"
                  value={portfolioValue}
                  onChange={(e) => setPortfolioValue(Number(e.target.value))}
                  min={1000}
                  step={1000}
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Objetivo</label>
                <select
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="max_sharpe">Maximizar Sharpe Ratio</option>
                  <option value="min_volatility">Minimizar Volatilidad</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Usar Analisis de Sentimiento</label>
                <div className="flex items-center gap-2 h-10">
                  <input
                    type="checkbox"
                    checked={useSentiment}
                    onChange={(e) => setUseSentiment(e.target. checked)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                  <span className="text-sm">
                    {useSentiment ? "Habilitado (Black-Litterman + FinBERT)" : "Deshabilitado"}
                  </span>
                </div>
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">{error}</div>
            )}

            <div className="flex gap-4">
              <Button onClick={runAnalysis} disabled={isLoading || tickers.length < 2} size="lg" className="gap-2">
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {step === "sentiment" && "Analizando sentimiento..."}
                    {step === "optimization" && "Optimizando portafolio..."}
                    {step === "risk" && "Calculando riesgo..."}
                  </>
                ) : (
                  <>
                    <PlayCircle className="h-4 w-4" />
                    Ejecutar Analisis Completo
                  </>
                )}
              </Button>

              {step === "complete" && (
                <Button variant="outline" onClick={runAnalysis} className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  Recalcular
                </Button>
              )}
            </div>

            {isLoading && (
              <div className="flex items-center gap-4">
                <div className={`flex items-center gap-2 ${step === "sentiment" ? "text-blue-600" : "text-muted-foreground"}`}>
                  <div className={`h-2 w-2 rounded-full ${step === "sentiment" ? "bg-blue-600 animate-pulse" : sentimentData ?  "bg-green-500" :  "bg-gray-300"}`} />
                  Sentimiento
                </div>
                <div className={`flex items-center gap-2 ${step === "optimization" ? "text-blue-600" : "text-muted-foreground"}`}>
                  <div className={`h-2 w-2 rounded-full ${step === "optimization" ? "bg-blue-600 animate-pulse" : optimizationData ? "bg-green-500" : "bg-gray-300"}`} />
                  Optimizacion
                </div>
                <div className={`flex items-center gap-2 ${step === "risk" ? "text-blue-600" : "text-muted-foreground"}`}>
                  <div className={`h-2 w-2 rounded-full ${step === "risk" ? "bg-blue-600 animate-pulse" : riskData ? "bg-green-500" : "bg-gray-300"}`} />
                  Riesgo
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {step === "complete" && optimizationData && riskData && (
          <div className="space-y-8">
            <MetricsSummary metrics={optimizationData.metrics} portfolioValue={portfolioValue} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PortfolioChart allocations={optimizationData.allocations} />
              {optimizationData.efficient_frontier && optimizationData.efficient_frontier. length > 0 && (
                <EfficientFrontier
                  frontierPoints={optimizationData.efficient_frontier}
                  currentPortfolio={{
                    return: optimizationData.metrics.expected_annual_return,
                    volatility: optimizationData.metrics. annual_volatility,
                  }}
                />
              )}
            </div>

            {sentimentData && (
              <SentimentCard results={sentimentData. results} marketIndex={sentimentData.market_sentiment_index} />
            )}

            <RiskMetrics metrics={riskData.risk_metrics} portfolioValue={portfolioValue} />

            <MonteCarloChart samplePaths={riskData.monte_carlo. sample_paths} portfolioValue={portfolioValue} />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Prob. Ganancia</p>
                  <p className="text-2xl font-bold text-green-600">
                    {(riskData.monte_carlo.prob_profit * 100).toFixed(1)}%
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Prob. Ganancia &gt;20%</p>
                  <p className="text-2xl font-bold text-green-600">
                    {(riskData.monte_carlo. prob_gain_gt_20 * 100).toFixed(1)}%
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Prob. Perdida &gt;10%</p>
                  <p className="text-2xl font-bold text-red-600">
                    {(riskData.monte_carlo.prob_loss_gt_10 * 100).toFixed(1)}%
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">Valor Mediano (1 año)</p>
                  <p className="text-2xl font-bold">${riskData.monte_carlo.median_final_value. toLocaleString()}</p>
                </CardContent>
              </Card>
            </div>

            <StressScenarios scenarios={riskData.stress_scenarios} portfolioValue={portfolioValue} />

            <Card>
              <CardHeader>
                <CardTitle>Contribucion al Riesgo por Activo</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(riskData.risk_contribution)
                    .sort(([, a], [, b]) => b - a)
                    .map(([ticker, contribution]) => (
                      <div key={ticker} className="flex items-center gap-4">
                        <span className="w-16 font-medium">{ticker}</span>
                        <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${contribution}%` }} />
                        </div>
                        <span className="w-16 text-right text-sm font-medium">{contribution.toFixed(1)}%</span>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </main>

      <footer className="border-t mt-12 py-6 text-center text-sm text-muted-foreground">
        <p>Smart Asset Allocator - Optimizacion de portafolios con Black-Litterman, FinBERT y Monte Carlo</p>
      </footer>
    </div>
  );
}
