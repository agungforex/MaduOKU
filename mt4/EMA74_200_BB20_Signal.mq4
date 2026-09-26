#property copyright "MaduOKU"
#property strict
#property indicator_chart_window

#property indicator_buffers 9
#property indicator_plots   9

#property indicator_type1   DRAW_LINE
#property indicator_color1  clrOrange
#property indicator_width1  2
#property indicator_label1  "EMA Fast"

#property indicator_type2   DRAW_LINE
#property indicator_color2  clrDodgerBlue
#property indicator_width2  2
#property indicator_label2  "EMA Slow"

#property indicator_type3   DRAW_LINE
#property indicator_color3  clrSilver
#property indicator_label3  "BB Upper"

#property indicator_type4   DRAW_LINE
#property indicator_color4  clrSilver
#property indicator_label4  "BB Lower"

#property indicator_type5   DRAW_LINE
#property indicator_color5  clrGray
#property indicator_style5  STYLE_DOT
#property indicator_label5  "BB Basis"

#property indicator_type6   DRAW_ARROW
#property indicator_color6  clrLime
#property indicator_width6  2
#property indicator_label6  "Buy Signal 1"

#property indicator_type7   DRAW_ARROW
#property indicator_color7  clrRed
#property indicator_width7  2
#property indicator_label7  "Sell Signal 1"

#property indicator_type8   DRAW_ARROW
#property indicator_color8  clrLimeGreen
#property indicator_width8  1
#property indicator_label8  "Buy Signal 2"

#property indicator_type9   DRAW_ARROW
#property indicator_color9  clrMaroon
#property indicator_width9  1
#property indicator_label9  "Sell Signal 2"

input int    EmaFastPeriod = 74;
input int    EmaSlowPeriod = 200;
input int    BBPeriod      = 20;
input double BBDeviation   = 2.0;
input bool   RequireBOS    = true;  // Signal valid hanya jika searah BOS terakhir
input int    BosLookback   = 50;    // BOS harus terjadi dalam N candle terakhir
input int    ArrowGapPoints = 10;
input bool   EnableAlerts  = true;
input bool   EnablePushNotification = false;

double EmaFastBuffer[];
double EmaSlowBuffer[];
double BBUpperBuffer[];
double BBLowerBuffer[];
double BBBasisBuffer[];
double BuySignal1Buffer[];
double SellSignal1Buffer[];
double BuySignal2Buffer[];
double SellSignal2Buffer[];

datetime lastBuy1AlertTime  = 0;
datetime lastSell1AlertTime = 0;
datetime lastBuy2AlertTime  = 0;
datetime lastSell2AlertTime = 0;

int OnInit()
{
   SetIndexBuffer(0, EmaFastBuffer);
   SetIndexBuffer(1, EmaSlowBuffer);
   SetIndexBuffer(2, BBUpperBuffer);
   SetIndexBuffer(3, BBLowerBuffer);
   SetIndexBuffer(4, BBBasisBuffer);
   SetIndexBuffer(5, BuySignal1Buffer);
   SetIndexBuffer(6, SellSignal1Buffer);
   SetIndexBuffer(7, BuySignal2Buffer);
   SetIndexBuffer(8, SellSignal2Buffer);

   ArraySetAsSeries(EmaFastBuffer, true);
   ArraySetAsSeries(EmaSlowBuffer, true);
   ArraySetAsSeries(BBUpperBuffer, true);
   ArraySetAsSeries(BBLowerBuffer, true);
   ArraySetAsSeries(BBBasisBuffer, true);
   ArraySetAsSeries(BuySignal1Buffer, true);
   ArraySetAsSeries(SellSignal1Buffer, true);
   ArraySetAsSeries(BuySignal2Buffer, true);
   ArraySetAsSeries(SellSignal2Buffer, true);

   SetIndexArrow(5, 233); // Signal 1 panah atas
   SetIndexArrow(6, 234); // Signal 1 panah bawah
   SetIndexArrow(7, 159); // Signal 2 titik atas
   SetIndexArrow(8, 159); // Signal 2 titik bawah
   SetIndexEmptyValue(5, EMPTY_VALUE);
   SetIndexEmptyValue(6, EMPTY_VALUE);
   SetIndexEmptyValue(7, EMPTY_VALUE);
   SetIndexEmptyValue(8, EMPTY_VALUE);

   IndicatorShortName("EMA " + IntegerToString(EmaFastPeriod) + "/" + IntegerToString(EmaSlowPeriod) + " + BB " + IntegerToString(BBPeriod));
   return(INIT_SUCCEEDED);
}

// Cari BOS (Break of Structure) terakhir dalam N candle terakhir, dihitung dari sudut pandang
// candle "refShift" (0 = candle sekarang, dst). Swing high/low pakai fractal 5-bar, validasi close.
// Return: 1 = BOS bullish terakhir, -1 = BOS bearish terakhir, 0 = tidak ada BOS dalam lookback.
int GetBOSDirectionAt(const double &high[], const double &low[], const double &close[],
                       int refShift, int lookback, int totalBars)
{
   double swingHigh = -1.0;
   double swingLow  = -1.0;
   int    lastBOS    = 0;

   int scanStartRel = lookback + 20;

   for(int rel = scanStartRel; rel >= 3; rel--)
   {
      int idx = refShift + rel - 1;
      if(idx - 2 < 0 || idx + 2 >= totalBars)
         continue;

      bool isFractalHigh = high[idx] > high[idx-1] && high[idx] > high[idx-2] && high[idx] > high[idx+1] && high[idx] > high[idx+2];
      bool isFractalLow  = low[idx]  < low[idx-1]  && low[idx]  < low[idx-2]  && low[idx]  < low[idx+1]  && low[idx]  < low[idx+2];

      if(isFractalHigh) swingHigh = high[idx];
      if(isFractalLow)  swingLow  = low[idx];

      if(rel <= lookback)
      {
         double c = close[idx];
         if(swingHigh > 0 && c > swingHigh)
         {
            lastBOS = 1;
            swingHigh = -1.0;
         }
         else if(swingLow > 0 && c < swingLow)
         {
            lastBOS = -1;
            swingLow = -1.0;
         }
      }
   }

   return lastBOS;
}

int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   if(rates_total <= EmaSlowPeriod + 2)
      return(0);

   int limit;
   if(prev_calculated == 0)
      limit = rates_total - EmaSlowPeriod - 2;
   else
      limit = rates_total - prev_calculated + 1;

   if(limit > rates_total - EmaSlowPeriod - 2)
      limit = rates_total - EmaSlowPeriod - 2;
   if(limit < 0)
      limit = 0;

   double gap = ArrowGapPoints * Point;

   for(int i = limit; i >= 0; i--)
   {
      EmaFastBuffer[i] = iMA(NULL, 0, EmaFastPeriod, 0, MODE_EMA, PRICE_CLOSE, i);
      EmaSlowBuffer[i] = iMA(NULL, 0, EmaSlowPeriod, 0, MODE_EMA, PRICE_CLOSE, i);
      BBUpperBuffer[i] = iBands(NULL, 0, BBPeriod, BBDeviation, 0, PRICE_CLOSE, MODE_UPPER, i);
      BBLowerBuffer[i] = iBands(NULL, 0, BBPeriod, BBDeviation, 0, PRICE_CLOSE, MODE_LOWER, i);
      BBBasisBuffer[i] = iBands(NULL, 0, BBPeriod, BBDeviation, 0, PRICE_CLOSE, MODE_MAIN, i);

      BuySignal1Buffer[i]  = EMPTY_VALUE;
      SellSignal1Buffer[i] = EMPTY_VALUE;
      BuySignal2Buffer[i]  = EMPTY_VALUE;
      SellSignal2Buffer[i] = EMPTY_VALUE;

      if(i + 1 > rates_total - 1)
         continue;

      double emaFastPrev  = iMA(NULL, 0, EmaFastPeriod, 0, MODE_EMA, PRICE_CLOSE, i + 1);
      double basisPrev    = iBands(NULL, 0, BBPeriod, BBDeviation, 0, PRICE_CLOSE, MODE_MAIN, i + 1);

      bool emaFastUp   = EmaFastBuffer[i] > emaFastPrev;
      bool emaFastDown = EmaFastBuffer[i] < emaFastPrev;
      bool basisUp     = BBBasisBuffer[i] > basisPrev;
      bool basisDown   = BBBasisBuffer[i] < basisPrev;

      bool bosBullish = true;
      bool bosBearish = true;
      if(RequireBOS)
      {
         int bosDir = GetBOSDirectionAt(high, low, close, i, BosLookback, rates_total);
         bosBullish = (bosDir == 1);
         bosBearish = (bosDir == -1);
      }

      // Signal 1: breakout BB20 searah slope EMA74
      bool breakoutUp   = close[i] > BBUpperBuffer[i] && close[i + 1] <= BBUpperBuffer[i + 1];
      bool breakoutDown = close[i] < BBLowerBuffer[i] && close[i + 1] >= BBLowerBuffer[i + 1];

      if(breakoutUp && emaFastUp && bosBullish)
         BuySignal1Buffer[i] = low[i] - gap;

      if(breakoutDown && emaFastDown && bosBearish)
         SellSignal1Buffer[i] = high[i] + gap;

      // Signal 2: cross garis tengah BB20, filter slope basis ATAU slope EMA74 searah
      bool crossBasisUp   = close[i] > BBBasisBuffer[i] && close[i + 1] <= BBBasisBuffer[i + 1];
      bool crossBasisDown = close[i] < BBBasisBuffer[i] && close[i + 1] >= BBBasisBuffer[i + 1];

      if(crossBasisUp && (basisUp || emaFastUp) && bosBullish)
         BuySignal2Buffer[i] = low[i] - gap;

      if(crossBasisDown && (basisDown || emaFastDown) && bosBearish)
         SellSignal2Buffer[i] = high[i] + gap;
   }

   if(EnableAlerts || EnablePushNotification)
      CheckAlerts(time);

   return(rates_total);
}

void CheckAlerts(const datetime &time[])
{
   if(BuySignal1Buffer[1] != EMPTY_VALUE && time[1] != lastBuy1AlertTime)
   {
      lastBuy1AlertTime = time[1];
      string msg = Symbol() + " " + EnumToString((ENUM_TIMEFRAMES)Period()) + ": BUY Signal 1 (BB20 breakout, EMA74 uptrend)";
      if(EnableAlerts) Alert(msg);
      if(EnablePushNotification) SendNotification(msg);
   }

   if(SellSignal1Buffer[1] != EMPTY_VALUE && time[1] != lastSell1AlertTime)
   {
      lastSell1AlertTime = time[1];
      string msg = Symbol() + " " + EnumToString((ENUM_TIMEFRAMES)Period()) + ": SELL Signal 1 (BB20 breakout, EMA74 downtrend)";
      if(EnableAlerts) Alert(msg);
      if(EnablePushNotification) SendNotification(msg);
   }

   if(BuySignal2Buffer[1] != EMPTY_VALUE && time[1] != lastBuy2AlertTime)
   {
      lastBuy2AlertTime = time[1];
      string msg = Symbol() + " " + EnumToString((ENUM_TIMEFRAMES)Period()) + ": BUY Signal 2 (cross BB basis, slope searah)";
      if(EnableAlerts) Alert(msg);
      if(EnablePushNotification) SendNotification(msg);
   }

   if(SellSignal2Buffer[1] != EMPTY_VALUE && time[1] != lastSell2AlertTime)
   {
      lastSell2AlertTime = time[1];
      string msg = Symbol() + " " + EnumToString((ENUM_TIMEFRAMES)Period()) + ": SELL Signal 2 (cross BB basis, slope searah)";
      if(EnableAlerts) Alert(msg);
      if(EnablePushNotification) SendNotification(msg);
   }
}
