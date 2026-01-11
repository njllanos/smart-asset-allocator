import axios from "axios";

const API_BASE_URL = process.env. NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Types
export interface AssetStatistics {
  ticker: string;
  annualized_return: number;
  annualized_volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  last_price: number;
  price_change_1y: number | null;
}

export interface MarketDataResponse {
  tickers: string[];
  statistics: Record<string, AssetStatistics>;
  covariance_matrix: Record<string, Record<string, number>>;
  correlation_matrix: Record<string, Record<string, number>>;
  data_start_date: string;
  data_end_date: string;
  trading_days: number;
}

export interface SentimentResult {
  ticker: string;
  sentiment_score: number;
  dominant_sentiment: string;
  confidence_avg: number;
  articles_analyzed: number;
  positive_ratio: number;
  negative_ratio: number;
  neutral_ratio: number;
}

export interface SentimentResponse {
  analysis_timestamp: string;
  tickers_analyzed: string[];
  results:  Record<string, SentimentResult>;
  market_sentiment_index:  number;
  model_used: string;
}

export interface PortfolioAllocation {
  ticker: string;
  weight: number;
  weight_percent: number;
  expected_return: number;
}

export interface PortfolioMetrics {
  expected_annual_return: number;
  annual_volatility: number;
  sharpe_ratio: number;
}

export interface OptimizationResponse {
  optimization_timestamp: string;
  objective_used: string;
  tickers:  string[];
  allocations: PortfolioAllocation[];
  weights: Record<string, number>;
  metrics: PortfolioMetrics;
  black_litterman_params: {
    tau: number;
    market_implied_returns: Record<string, number>;
    posterior_returns: Record<string, number>;
    views_applied: Record<string, number>;
  } | null;
  sentiment_views_used: boolean;
  efficient_frontier: Array<{ return: number; volatility: number; sharpe:  number }>;
}

export interface VaRResult {
  confidence_level: number;
  var_percent: number;
  var_amount: number;
  expected_shortfall: number;
  es_percent: number;
}

export interface MonteCarloPath {
  percentile: string;
  values: number[];
}

export interface StressScenario {
  scenario_name: string;
  description: string;
  portfolio_impact_percent: number;
  portfolio_impact_amount: number;
  var_under_stress: number;
}

export interface RiskAnalysisResponse {
  analysis_timestamp: string;
  portfolio_value: number;
  tickers:  string[];
  weights: Record<string, number>;
  risk_metrics: {
    daily_volatility: number;
    annual_volatility: number;
    var_results: VaRResult[];
    max_drawdown: number;
    avg_drawdown: number;
    skewness: number;
    kurtosis: number;
    prob_loss_1_percent: number;
    prob_loss_5_percent: number;
    prob_loss_10_percent: number;
  };
  monte_carlo:  {
    num_simulations: number;
    simulation_days: number;
    mean_final_value: number;
    median_final_value: number;
    std_final_value: number;
    min_final_value: number;
    max_final_value: number;
    percentile_5: number;
    percentile_95: number;
    prob_profit:  number;
    prob_loss_gt_10: number;
    prob_loss_gt_20: number;
    prob_gain_gt_10: number;
    prob_gain_gt_20: number;
    sample_paths: MonteCarloPath[];
  };
  stress_scenarios: StressScenario[];
  risk_contribution: Record<string, number>;
  correlation_matrix: Record<string, Record<string, number>>;
}

// API Functions
export const marketDataApi = {
  getMarketData: async (tickers: string[], timeframe: string = "3y"): Promise<MarketDataResponse> => {
    const response = await api.post("/market-data/", { tickers, timeframe });
    return response.data;
  },
};

export const sentimentApi = {
  analyzeSentiment: async (tickers: string[], maxArticles: number = 25): Promise<SentimentResponse> => {
    const response = await api. post("/sentiment/analyze", {
      tickers,
      max_articles_per_ticker: maxArticles,
    });
    return response.data;
  },
};

export const optimizationApi = {
  optimize: async (
    tickers:  string[],
    objective: string = "max_sharpe",
    useSentiment: boolean = true,
    timeframe: string = "3y",
    constraints?:  { min_weight?:  number; max_weight?: number }
  ): Promise<OptimizationResponse> => {
    const response = await api.post("/optimization/optimize", {
      tickers,
      timeframe,
      objective,
      use_sentiment: useSentiment,
      constraints:  constraints || { min_weight: 0, max_weight: 1 },
    });
    return response.data;
  },
};

export const riskApi = {
  analyzeRisk: async (
    tickers: string[],
    weights: Record<string, number>,
    portfolioValue: number = 100000,
    numSimulations: number = 5000
  ): Promise<RiskAnalysisResponse> => {
    const response = await api.post("/risk/analyze", {
      tickers,
      weights,
      portfolio_value: portfolioValue,
      num_simulations: numSimulations,
    });
    return response.data;
  },
};

export default api;
