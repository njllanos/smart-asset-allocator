"use client";

import React, { useState } from "react";
import { X, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface TickerInputProps {
  tickers: string[];
  onTickersChange: (tickers: string[]) => void;
  maxTickers?: number;
}

const POPULAR_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ"];

export function TickerInput({ tickers, onTickersChange, maxTickers = 10 }: TickerInputProps) {
  const [inputValue, setInputValue] = useState("");

  const addTicker = (ticker: string) => {
    const normalized = ticker.toUpperCase().trim();
    if (normalized && ! tickers.includes(normalized) && tickers.length < maxTickers) {
      onTickersChange([...tickers, normalized]);
    }
    setInputValue("");
  };

  const removeTicker = (ticker: string) => {
    onTickersChange(tickers.filter((t) => t !== ticker));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e. key === "Enter") {
      e.preventDefault();
      addTicker(inputValue);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          placeholder="Agregar ticker (ej: AAPL)"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          className="flex-1"
        />
        <Button onClick={() => addTicker(inputValue)} disabled={!inputValue || tickers.length >= maxTickers}>
          <Plus className="h-4 w-4 mr-1" /> Agregar
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {tickers.map((ticker) => (
          <Badge key={ticker} variant="secondary" className="text-sm py-1 px-3">
            {ticker}
            <button onClick={() => removeTicker(ticker)} className="ml-2 hover: text-destructive">
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>

      {tickers.length < maxTickers && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">Populares: </p>
          <div className="flex flex-wrap gap-2">
            {POPULAR_TICKERS.filter((t) => !tickers.includes(t)).map((ticker) => (
              <Button key={ticker} variant="outline" size="sm" onClick={() => addTicker(ticker)}>
                {ticker}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
