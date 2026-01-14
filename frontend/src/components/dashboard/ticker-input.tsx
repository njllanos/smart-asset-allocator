"use client";

import React, { useState } from "react";
import { X, Plus, Check, TrendingUp, Search } from "lucide-react"; // Agregamos iconos
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
    if (normalized && !tickers.includes(normalized) && tickers.length < maxTickers) {
      onTickersChange([...tickers, normalized]);
    }
    setInputValue("");
  };

  const removeTicker = (ticker: string) => {
    onTickersChange(tickers.filter((t) => t !== ticker));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTicker(inputValue);
    }
  };

  return (
    <div className="space-y-6">
      {/* SECCIÓN 1: INPUT DE BÚSQUEDA */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Escribe un ticker (ej: NVDA)..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            className="pl-9"
          />
        </div>
        <Button 
            onClick={() => addTicker(inputValue)} 
            disabled={!inputValue || tickers.length >= maxTickers}
            className="bg-slate-900 text-white hover:bg-slate-800"
        >
          <Plus className="h-4 w-4 mr-1" /> Agregar
        </Button>
      </div>

      {/* SECCIÓN 2: LA CANASTA DE ACTIVOS (NUEVO DISEÑO) */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 shadow-inner">
        <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-blue-600"/>
                Tu Portafolio Seleccionado
            </h3>
            <span className={`text-xs font-mono px-2 py-1 rounded-full border ${tickers.length === maxTickers ? 'bg-amber-100 text-amber-700 border-amber-200' : 'bg-white text-slate-500 border-slate-200'}`}>
                {tickers.length} / {maxTickers} activos
            </span>
        </div>

        {tickers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-6 text-center border-2 border-dashed border-slate-200 rounded-lg">
                <p className="text-sm text-slate-400 font-medium">Tu portafolio está vacío</p>
                <p className="text-xs text-slate-400 mt-1">Agrega tickers arriba o selecciona populares abajo</p>
            </div>
        ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {tickers.map((ticker) => (
                <div 
                    key={ticker} 
                    className="group flex items-center justify-between bg-white border border-blue-100 hover:border-blue-300 hover:shadow-md transition-all p-2 rounded-lg pl-3"
                >
                    <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-blue-500 ring-2 ring-blue-100"></div>
                        <span className="font-bold text-slate-700">{ticker}</span>
                    </div>
                    <button 
                        onClick={() => removeTicker(ticker)} 
                        className="text-slate-300 hover:text-red-500 hover:bg-red-50 p-1 rounded-md transition-colors"
                        title="Eliminar activo"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
                ))}
            </div>
        )}
      </div>

      {/* SECCIÓN 3: SUGERENCIAS */}
      {tickers.length < maxTickers && (
        <div className="space-y-2 pt-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Sugerencias Populares</p>
          <div className="flex flex-wrap gap-2">
            {POPULAR_TICKERS.filter((t) => !tickers.includes(t)).map((ticker) => (
              <button 
                key={ticker} 
                onClick={() => addTicker(ticker)}
                className="text-xs border border-slate-200 bg-white text-slate-600 hover:border-blue-300 hover:text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-full transition-all flex items-center gap-1"
              >
                <Plus className="h-3 w-3" />
                {ticker}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
