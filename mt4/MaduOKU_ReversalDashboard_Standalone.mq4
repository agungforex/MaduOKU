#property copyright "MaduOKU"
#property strict
#property indicator_chart_window
#property indicator_plots 0

//========================================================================
// Standalone version: pure MQL4, no Python/file bridge needed. Computes
// a rule-based reversal score natively from RSI, MACD, Bollinger Bands,
// RSI/price divergence and candlestick patterns, for M5/M15/H1/H4 at
// once. Drop it on any chart and it works immediately.
//
// This trades away the trained ML model (from the Python pipeline) for
// zero setup: no cronjob, no Task Scheduler, no shared files. If you
// want the better-tuned ML signals instead, use
// MaduOKU_ReversalDashboard.mq4 + scripts/export_mt4_signal.py.
//========================================================================

//--- inputs
input string            InpSymbolOverride = "";              // Override symbol (blank = use chart symbol)
input int                InpRefreshSeconds = 5;                // Refresh interval (seconds)
input int                InpFontSize       = 9;                // Font size
input int                InpMinScore       = 2;                // Min aligned signals required to flag a reversal
input int                InpDivergenceLookback = 20;           // Bars per side for divergence check
input color              InpBullishColor   = clrLimeGreen;
input color              InpBearishColor   = clrTomato;
input color              InpNoneColor      = clrSilver;
input color              InpLoadingColor   = clrGray;
input ENUM_BASE_CORNER   InpCorner         = CORNER_LEFT_UPPER;
input int                InpXOffset        = 10;
input int                InpYOffset        = 20;

int    g_timeframes[4] = {PERIOD_M5, PERIOD_M15, PERIOD_H1, PERIOD_H4};
string g_tf_labels[4]  = {"M5", "M15", "H1", "H4"};

string g_prefix = "MaduOKU_SA_";
string g_symbol;

int OnInit()
{
   g_symbol = (InpSymbolOverride != "") ? InpSymbolOverride : Symbol();
   CreateDashboard();
   EventSetTimer(MathMax(InpRefreshSeconds, 1));
   RefreshDashboard();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, g_prefix);
}

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[], const double &open[],
                const double &high[], const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   return(rates_total);
}

void OnTimer()
{
   RefreshDashboard();
}

void CreateDashboard()
{
   int rowHeight = InpFontSize + 10;
   CreateLabel(g_prefix + "Title", g_symbol + " - Reversal Watch (standalone)", InpXOffset, InpYOffset, InpFontSize + 2, clrWhite);
   for(int i = 0; i < 4; i++)
   {
      int y = InpYOffset + (i + 1) * rowHeight;
      CreateLabel(g_prefix + "TF_" + g_tf_labels[i], g_tf_labels[i] + ":", InpXOffset, y, InpFontSize, clrSilver);
      CreateLabel(g_prefix + "Sig_" + g_tf_labels[i], "loading...", InpXOffset + 45, y, InpFontSize, InpLoadingColor);
   }
}

void CreateLabel(string name, string text, int x, int y, int fontSize, color clr)
{
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, name, OBJPROP_CORNER, InpCorner);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
   ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
}

void RefreshDashboard()
{
   for(int i = 0; i < 4; i++)
   {
      int tf = g_timeframes[i];
      string labelName = g_prefix + "Sig_" + g_tf_labels[i];

      if(iBars(g_symbol, tf) < 2 * InpDivergenceLookback + 5)
      {
         ObjectSetString(0, labelName, OBJPROP_TEXT, "loading history...");
         ObjectSetInteger(0, labelName, OBJPROP_COLOR, InpLoadingColor);
         continue;
      }

      int    signal;
      double confidence;
      ComputeSignal(g_symbol, tf, signal, confidence);

      color  clr;
      string display;
      if(signal == 1)
      {
         clr = InpBullishColor;
         display = StringFormat("BULLISH (%.0f%%)", confidence);
      }
      else if(signal == 2)
      {
         clr = InpBearishColor;
         display = StringFormat("BEARISH (%.0f%%)", confidence);
      }
      else
      {
         clr = InpNoneColor;
         display = "none";
      }

      ObjectSetString(0, labelName, OBJPROP_TEXT, display);
      ObjectSetInteger(0, labelName, OBJPROP_COLOR, clr);
   }
}

// signal: 0=none, 1=bullish reversal, 2=bearish reversal. confidencePct: 0-100.
void ComputeSignal(string symbol, int tf, int &signal, double &confidencePct)
{
   double rsi1 = iRSI(symbol, tf, 14, PRICE_CLOSE, 1);
   bool rsiOversold    = rsi1 < 30;
   bool rsiOverbought  = rsi1 > 70;

   double macdHist1 = iMACD(symbol, tf, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 1)
                     - iMACD(symbol, tf, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 1);
   double macdHist2 = iMACD(symbol, tf, 12, 26, 9, PRICE_CLOSE, MODE_MAIN, 2)
                     - iMACD(symbol, tf, 12, 26, 9, PRICE_CLOSE, MODE_SIGNAL, 2);
   bool macdCrossUp   = (macdHist1 > 0 && macdHist2 <= 0);
   bool macdCrossDown = (macdHist1 < 0 && macdHist2 >= 0);

   double upperBand = iBands(symbol, tf, 20, 2, 0, PRICE_CLOSE, MODE_UPPER, 1);
   double lowerBand = iBands(symbol, tf, 20, 2, 0, PRICE_CLOSE, MODE_LOWER, 1);
   double close1    = iClose(symbol, tf, 1);
   bool bbLowerTouch = close1 <= lowerBand;
   bool bbUpperTouch = close1 >= upperBand;

   bool bullishDiv = DetectDivergence(symbol, tf, true);
   bool bearishDiv = DetectDivergence(symbol, tf, false);

   bool bullishEngulfing = IsBullishEngulfing(symbol, tf);
   bool bearishEngulfing = IsBearishEngulfing(symbol, tf);
   bool hammer       = IsHammer(symbol, tf);
   bool shootingStar = IsShootingStar(symbol, tf);

   int bullScore = 0, bearScore = 0;
   if(rsiOversold)              bullScore += 1;
   if(rsiOverbought)            bearScore += 1;
   if(macdCrossUp)              bullScore += 1;
   if(macdCrossDown)            bearScore += 1;
   if(bbLowerTouch)             bullScore += 1;
   if(bbUpperTouch)             bearScore += 1;
   if(bullishDiv)                bullScore += 2;   // divergence weighted higher
   if(bearishDiv)                bearScore += 2;
   if(bullishEngulfing || hammer)       bullScore += 1;
   if(bearishEngulfing || shootingStar) bearScore += 1;

   int maxPossible = 7;

   if(bullScore >= InpMinScore && bullScore > bearScore)
   {
      signal = 1;
      confidencePct = MathMin(100.0, bullScore * 100.0 / maxPossible);
   }
   else if(bearScore >= InpMinScore && bearScore > bullScore)
   {
      signal = 2;
      confidencePct = MathMin(100.0, bearScore * 100.0 / maxPossible);
   }
   else
   {
      signal = 0;
      confidencePct = 0;
   }
}

// Bullish divergence: price makes a lower low while RSI makes a higher
// low (momentum fading on a downtrend). Bearish: price higher high,
// RSI lower high. Compares the extreme in the most recent window vs
// the window immediately before it.
bool DetectDivergence(string symbol, int tf, bool bullish)
{
   int w = InpDivergenceLookback;

   if(bullish)
   {
      int recentIdx = iLowest(symbol, tf, MODE_LOW, w, 1);
      int prevIdx   = iLowest(symbol, tf, MODE_LOW, w, 1 + w);
      double recentLow = iLow(symbol, tf, recentIdx);
      double prevLow    = iLow(symbol, tf, prevIdx);
      double recentRSI  = iRSI(symbol, tf, 14, PRICE_CLOSE, recentIdx);
      double prevRSI     = iRSI(symbol, tf, 14, PRICE_CLOSE, prevIdx);
      return (recentLow < prevLow) && (recentRSI > prevRSI);
   }
   else
   {
      int recentIdx = iHighest(symbol, tf, MODE_HIGH, w, 1);
      int prevIdx   = iHighest(symbol, tf, MODE_HIGH, w, 1 + w);
      double recentHigh = iHigh(symbol, tf, recentIdx);
      double prevHigh    = iHigh(symbol, tf, prevIdx);
      double recentRSI   = iRSI(symbol, tf, 14, PRICE_CLOSE, recentIdx);
      double prevRSI      = iRSI(symbol, tf, 14, PRICE_CLOSE, prevIdx);
      return (recentHigh > prevHigh) && (recentRSI < prevRSI);
   }
}

bool IsBullishEngulfing(string symbol, int tf)
{
   double o1 = iOpen(symbol, tf, 1), c1 = iClose(symbol, tf, 1);
   double o2 = iOpen(symbol, tf, 2), c2 = iClose(symbol, tf, 2);
   return (c1 > o1) && (c2 < o2) && (c1 >= o2) && (o1 <= c2);
}

bool IsBearishEngulfing(string symbol, int tf)
{
   double o1 = iOpen(symbol, tf, 1), c1 = iClose(symbol, tf, 1);
   double o2 = iOpen(symbol, tf, 2), c2 = iClose(symbol, tf, 2);
   return (c1 < o1) && (c2 > o2) && (o1 >= c2) && (c1 <= o2);
}

bool IsHammer(string symbol, int tf)
{
   double o = iOpen(symbol, tf, 1), c = iClose(symbol, tf, 1);
   double h = iHigh(symbol, tf, 1), l = iLow(symbol, tf, 1);
   double body  = MathAbs(c - o);
   double range = h - l;
   if(range <= 0) return(false);
   double lowerWick = MathMin(c, o) - l;
   double upperWick = h - MathMax(c, o);
   return (lowerWick >= 2 * body) && (upperWick <= 0.3 * MathMax(body, 0.00001)) && (body / range < 0.35);
}

bool IsShootingStar(string symbol, int tf)
{
   double o = iOpen(symbol, tf, 1), c = iClose(symbol, tf, 1);
   double h = iHigh(symbol, tf, 1), l = iLow(symbol, tf, 1);
   double body  = MathAbs(c - o);
   double range = h - l;
   if(range <= 0) return(false);
   double lowerWick = MathMin(c, o) - l;
   double upperWick = h - MathMax(c, o);
   return (upperWick >= 2 * body) && (lowerWick <= 0.3 * MathMax(body, 0.00001)) && (body / range < 0.35);
}
