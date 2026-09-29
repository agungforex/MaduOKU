#property copyright "MaduOKU"
#property link      ""
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 7
#property indicator_plots   5

#property indicator_color1  clrDodgerBlue   // EMA74
#property indicator_color2  clrOrangeRed    // EMA200
#property indicator_color3  clrSilver       // BB Upper
#property indicator_color4  clrSilver       // BB Lower
#property indicator_width1  2
#property indicator_width2  2

#property indicator_color5  clrLime         // Buy arrow
#property indicator_color6  clrRed          // Sell arrow
#property indicator_width5  2
#property indicator_width6  2

//--- Inputs -----------------------------------------------------------
input int    InpEmaFastPeriod   = 74;     // EMA cepat
input int    InpEmaSlowPeriod   = 200;    // EMA lambat
input int    InpBBPeriod        = 20;     // Periode Bollinger Bands
input double InpBBDeviation     = 2.0;    // Deviasi Bollinger Bands
input int    InpWaitBars        = 5;      // Window (bar) menunggu konfirmasi State3
input int    InpSLLookback      = 20;     // Jumlah candle untuk cari Low/High terjauh (SL)
input double InpSpreadMultiplier= 2.0;    // Kelipatan spread ditambahkan ke SL
input bool   ShowEmaBB          = true;   // Tampilkan EMA & BB di chart
input bool   ShowSLLines        = true;   // Gambar garis SL saat sinyal muncul
input bool   EnableAlert        = true;   // Alert popup
input bool   EnablePushNotify   = false;  // Push notification ke HP

//--- Buffers ------------------------------------------------------------
double EmaFastBuf[];
double EmaSlowBuf[];
double BBUpperBuf[];
double BBLowerBuf[];
double BBMidBuf[];
double BuyArrowBuf[];
double SellArrowBuf[];

//--- State machine (chronological, per direction) -----------------------
// pending = bar index (shift, 0 = current bar) where State2 terjadi; -1 = tidak ada state pending
int pendingBuyShift  = -1;
int pendingSellShift = -1;

int OnInit()
  {
   IndicatorBuffers(7);

   SetIndexBuffer(0, EmaFastBuf);
   SetIndexStyle(0, ShowEmaBB ? DRAW_LINE : DRAW_NONE);
   SetIndexLabel(0, "EMA " + IntegerToString(InpEmaFastPeriod));

   SetIndexBuffer(1, EmaSlowBuf);
   SetIndexStyle(1, ShowEmaBB ? DRAW_LINE : DRAW_NONE);
   SetIndexLabel(1, "EMA " + IntegerToString(InpEmaSlowPeriod));

   SetIndexBuffer(2, BBUpperBuf);
   SetIndexStyle(2, ShowEmaBB ? DRAW_LINE : DRAW_NONE, STYLE_DOT);
   SetIndexLabel(2, "BB Upper");

   SetIndexBuffer(3, BBLowerBuf);
   SetIndexStyle(3, ShowEmaBB ? DRAW_LINE : DRAW_NONE, STYLE_DOT);
   SetIndexLabel(3, "BB Lower");

   SetIndexBuffer(4, BBMidBuf);
   SetIndexStyle(4, DRAW_NONE);
   SetIndexLabel(4, "BB Mid");

   SetIndexBuffer(5, BuyArrowBuf);
   SetIndexStyle(5, DRAW_ARROW);
   SetIndexArrow(5, 233);
   SetIndexLabel(5, "Buy Signal");

   SetIndexBuffer(6, SellArrowBuf);
   SetIndexStyle(6, DRAW_ARROW);
   SetIndexArrow(6, 234);
   SetIndexLabel(6, "Sell Signal");

   IndicatorShortName("MaduOKU Scalping M1 (EMA" + IntegerToString(InpEmaFastPeriod) +
                       "/" + IntegerToString(InpEmaSlowPeriod) + ", BB" +
                       IntegerToString(InpBBPeriod) + "," + DoubleToString(InpBBDeviation, 1) + ")");
   return(INIT_SUCCEEDED);
  }

double GetSpreadInPrice()
  {
   double spreadPoints = MarketInfo(Symbol(), MODE_SPREAD);
   return(spreadPoints * Point);
  }

//--- Lowest Low / Highest High over InpSLLookback bars starting at 'shift'
double LowestLowFrom(int shift)
  {
   int idx = iLowest(NULL, 0, MODE_LOW, InpSLLookback, shift);
   return(idx >= 0 ? Low[idx] : Low[shift]);
  }

double HighestHighFrom(int shift)
  {
   int idx = iHighest(NULL, 0, MODE_HIGH, InpSLLookback, shift);
   return(idx >= 0 ? High[idx] : High[shift]);
  }

void DrawSLLine(string name, datetime t, double price, color clr)
  {
   if(!ShowSLLines)
      return;
   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_HLINE, 0, t, price);
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
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
   int minBarsNeeded = MathMax(InpEmaSlowPeriod, MathMax(InpBBPeriod, InpSLLookback)) + InpWaitBars + 5;
   if(rates_total < minBarsNeeded)
      return(0);

   int limit = rates_total - prev_calculated;
   if(prev_calculated == 0)
     {
      limit = rates_total - minBarsNeeded;
      pendingBuyShift  = -1;
      pendingSellShift = -1;
     }
   if(limit > rates_total - minBarsNeeded)
      limit = rates_total - minBarsNeeded;
   if(limit < 1)
      limit = 1;

   double spreadPrice = GetSpreadInPrice();

   // Iterasi dari bar terlama ke terbaru (shift besar -> shift kecil) agar state machine berjalan kronologis
   for(int shift = limit; shift >= 0; shift--)
     {
      int i = shift; // index array timeseries, 0 = bar terbaru

      double emaFast = iMA(NULL, 0, InpEmaFastPeriod, 0, MODE_EMA, PRICE_CLOSE, i);
      double emaSlow = iMA(NULL, 0, InpEmaSlowPeriod, 0, MODE_EMA, PRICE_CLOSE, i);
      double bbUpper = iBands(NULL, 0, InpBBPeriod, InpBBDeviation, 0, PRICE_CLOSE, MODE_UPPER, i);
      double bbLower = iBands(NULL, 0, InpBBPeriod, InpBBDeviation, 0, PRICE_CLOSE, MODE_LOWER, i);
      double bbMid   = iBands(NULL, 0, InpBBPeriod, InpBBDeviation, 0, PRICE_CLOSE, MODE_MAIN, i);

      EmaFastBuf[i] = emaFast;
      EmaSlowBuf[i] = emaSlow;
      BBUpperBuf[i] = bbUpper;
      BBLowerBuf[i] = bbLower;
      BBMidBuf[i]   = bbMid;
      BuyArrowBuf[i]  = EMPTY_VALUE;
      SellArrowBuf[i] = EMPTY_VALUE;

      bool trendUp   = emaFast > emaSlow;   // State 1 - BUY bias
      bool trendDown = emaFast < emaSlow;   // State 1 - SELL bias

      bool bearishCandle = close[i] < open[i];
      bool bullishCandle = close[i] > open[i];

      //================= BUY SIDE =================
      if(trendUp && bearishCandle && close[i] < bbLower)
        {
         // State 2 baru terjadi -> (re)set window tunggu
         pendingBuyShift = i;
        }
      else if(pendingBuyShift >= 0)
        {
         int barsElapsed = pendingBuyShift - i; // berapa bar sudah lewat sejak State2
         if(barsElapsed > InpWaitBars)
           {
            pendingBuyShift = -1; // window habis, invalid
           }
         else if(trendUp && bullishCandle && close[i] > bbLower)
           {
            // State 3 - Sinyal BUY
            BuyArrowBuf[i] = Low[i] - 3 * Point;
            double sl = LowestLowFrom(i) - InpSpreadMultiplier * spreadPrice;
            DrawSLLine("MaduOKU_SL_BUY_" + TimeToString(time[i]), time[i], sl, clrLime);

            if(i == 0) // hanya alert untuk bar yang baru terbentuk/berjalan
              {
               string msg = StringFormat("%s M1 BUY signal @ %s | SL=%s", Symbol(), DoubleToString(Close[0], Digits), DoubleToString(sl, Digits));
               if(EnableAlert) Alert(msg);
               if(EnablePushNotify) SendNotification(msg);
              }
            pendingBuyShift = -1;
           }
        }

      //================= SELL SIDE =================
      if(trendDown && bullishCandle && close[i] > bbUpper)
        {
         // State 2 baru terjadi -> (re)set window tunggu
         pendingSellShift = i;
        }
      else if(pendingSellShift >= 0)
        {
         int barsElapsed = pendingSellShift - i;
         if(barsElapsed > InpWaitBars)
           {
            pendingSellShift = -1;
           }
         else if(trendDown && bearishCandle && close[i] < bbUpper)
           {
            // State 3 - Sinyal SELL
            SellArrowBuf[i] = High[i] + 3 * Point;
            double sl = HighestHighFrom(i) + InpSpreadMultiplier * spreadPrice;
            DrawSLLine("MaduOKU_SL_SELL_" + TimeToString(time[i]), time[i], sl, clrRed);

            if(i == 0)
              {
               string msg = StringFormat("%s M1 SELL signal @ %s | SL=%s", Symbol(), DoubleToString(Close[0], Digits), DoubleToString(sl, Digits));
               if(EnableAlert) Alert(msg);
               if(EnablePushNotify) SendNotification(msg);
              }
            pendingSellShift = -1;
           }
        }
     }

   return(rates_total);
  }
