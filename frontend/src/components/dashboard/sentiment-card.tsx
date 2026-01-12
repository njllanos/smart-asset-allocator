"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { SentimentResult } from "@/lib/api";
// Importamos el tooltip
import { HelpTooltip } from "@/components/ui/help-tooltip";

interface SentimentCardProps {
  results: Record<string, SentimentResult>;
  marketIndex: number;
}

export function SentimentCard({ results, marketIndex }: SentimentCardProps) {
  const getSentimentColor = (score: number) => {
    if (score > 0.1) return "text-green-500";
    if (score < -0.1) return "text-red-500";
    return "text-yellow-500";
  };

  const getSentimentIcon = (score: number) => {
    if (score > 0.1) return <TrendingUp className="h-4 w-4" />;
    if (score < -0.1) return <TrendingDown className="h-4 w-4" />;
    return <Minus className="h-4 w-4" />;
  };

  const getSentimentBadge = (sentiment: string) => {
    switch (sentiment) {
      case "positive":  return <Badge variant="success">Bullish</Badge>;
      case "negative": return <Badge variant="destructive">Bearish</Badge>;
      default: return <Badge variant="secondary">Neutral</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center">
            Análisis de Sentimiento
            {/* TOOLTIP EXPLICATIVO SOBRE IA */}
            <HelpTooltip content="Análisis de noticias financieras en tiempo real usando FinBERT (un modelo de IA especializado). Un puntaje positivo indica optimismo en el mercado, lo cual se usa como una 'View' (opinión) para ajustar las proyecciones matemáticas del modelo Black-Litterman." />
          </div>
          
          <div className={`flex items-center gap-2 ${getSentimentColor(marketIndex)}`}>
            {getSentimentIcon(marketIndex)}
            <span className="text-lg font-bold">{(marketIndex * 100).toFixed(1)}%</span>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Object.values(results).map((result) => (
            <div key={result.ticker} className="flex items-center justify-between p-3 bg-muted rounded-lg">
              <div className="flex items-center gap-3">
                <span className="font-semibold">{result.ticker}</span>
                {getSentimentBadge(result.dominant_sentiment)}
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className={`font-medium ${getSentimentColor(result.sentiment_score)}`}>
                    {(result.sentiment_score * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-muted-foreground">{result.articles_analyzed} artículos</p>
                </div>
                <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: `${result.positive_ratio * 100}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
