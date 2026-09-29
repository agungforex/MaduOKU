#property copyright "MaduOKU"
#property link      ""
#property version   "2.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 7
#property indicator_plots   5

#property indicator_color1  clrDodgerBlue   // EMA fast
#property indicator_color2  clrOrangeRed    // EMA slow
#property indicator_color3  clrSilver       // BB Upper
#property indicator_color4  clrSilver       // BB Lower
#property indicator_width1  2
#property indicator_width2  2

#property indicator_color5  clrLime         // Buy arrow
#property indicator_color6  clrRed          // Sell arrow
#property indicator_width5  2
#property indicator_width6  2

//--- Inputs -----------------------------------------------------------
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M1;  // Timeframe data yang dibaca (boleh beda dari chart)
input int    InpEmaFastPeriod   = 74;     // EMA cepat
input int    InpEmaSlowPeriod   = 200;    // EMA lambat
input int    InpBBPeriod        = 20;     // Periode Bollinger Bands
input double InpBBDeviation     = 2.0;    // Deviasi Bollinger Bands
input int    InpWaitBars        = 5;      // Window (bar) menunggu konfirmasi State3
input int    InpSLLookback      = 20;     // Jumlah candle untuk cari Low/High terjauh (SL)
input double InpSpreadMultiplier= 2.0;    // Kelipatan spread ditambahkan ke SL
input int    InpMaxTfBars       = 3000;   // Batas maksimal candle TF yang diproses (performa)
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

//--- dipakai supaya alert tidak diulang tiap tick pada bar TF yang sama
datetime lastBuyAlertTfTime  = 0;
datetime lastSellAlertTfTime = 0;

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

   IndicatorShortName("MaduOKU Scalping (" + EnumToString(InpTimeframe) + ", EMA" +
                       IntegerToString(InpEmaFastPeriod) + "/" + IntegerToString(InpEmaSlowPeriod) +
                       ", BB" + IntegerToString(InpBBPeriod) + "," + DoubleToString(InpBBDeviation, 1) + ")");
   return(INIT_SUCCEEDED);
  }

double GetSpreadInPrice()
  {
   return(MarketInfo(Symbol(), MODE_SPREAD) * Point);
  }

double LowestLowFrom(int tfShift)
  {
   int idx = iLowest(Symbol(), InpTimeframe, MODE_LOW, InpSLLookback, tfShift);
   return(idx >= 0 ? iLow(Symbol(), InpTimeframe, idx) : iLow(Symbol(), InpTimeframe, tfShift));
  }

double HighestHighFrom(int tfShift)
  {
   int idx = iHighest(Symbol(), InpTimeframe, MODE_HIGH, InpSLLookback, tfShift);
   return(idx >= 0 ? iHigh(Symbol(), InpTimeframe, idx) : iHigh(Symbol(), InpTimeframe, tfShift));
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
   int minTfBarsNeeded = MathMax(InpEmaSlowPeriod, MathMax(InpBBPeriod, InpSLLookback)) + InpWaitBars + 5;

   int tfTotal = iBars(Symbol(), InpTimeframe);
   if(tfTotal < minTfBarsNeeded)
      return(0); // data TF yang diminta belum cukup / belum ter-load

   int tfProcessCount = MathMin(tfTotal - minTfBarsNeeded, InpMaxTfBars);
   if(tfProcessCount < 1)
      return(0);

   //--- 1) Hitung state machine di timeframe target (InpTimeframe), simpan hasil per tf-bar
   int    tfType[];   // 1 = sinyal BUY, -1 = sinyal SELL, 0 = tidak ada
   double tfSL[];
   ArrayResize(tfType, tfProcessCount + 1);
   ArrayResize(tfSL,   tfProcessCount + 1);
   ArrayInitialize(tfType, 0);
   ArrayInitialize(tfSL, 0.0);

   double spreadPrice = GetSpreadInPrice();
   int pendingBuyTf  = -1;
   int pendingSellTf = -1;

   for(int tf = tfProcessCount; tf >= 0; tf--)
     {
      double o = iOpen(Symbol(), InpTimeframe, tf);
      double c = iClose(Symbol(), InpTimeframe, tf);

      double emaFast = iMA(Symbol(), InpTimeframe, InpEmaFastPeriod, 0, MODE_EMA, PRICE_CLOSE, tf);
      double emaSlow = iMA(Symbol(), InpTimeframe, InpEmaSlowPeriod, 0, MODE_EMA, PRICE_CLOSE, tf);
      double bbUpper = iBands(Symbol(), InpTimeframe, InpBBPeriod, InpBBDeviation, 0, PRICE_CLOSE, MODE_UPPER, tf);
      double bbLower = iBands(Symbol(), InpTimeframe, InpBBPeriod, InpBBDeviation, 0, PRICE_CLOSE, MODE_LOWER, tf);

      bool trendUp   = emaFast > emaSlow;
      bool trendDown = emaFast < emaSlow;
      bool bearishCandle = c < o;
      bool bullishCandle = c > o;

      //================= BUY SIDE =================
      if(trendUp && bearishCandle && c < bbLower)
        {
         pendingBuyTf = tf;
        }
      else if(pendingBuyTf >= 0)
        {
         int barsElapsed = pendingBuyTf - tf;
         if(barsElapsed > InpWaitBars)
           {
            pendingBuyTf = -1;
           }
         else if(trendUp && bullishCandle && c > bbLower)
           {
            tfType[tf] = 1;
            tfSL[tf]   = LowestLowFrom(tf) - InpSpreadMultiplier * spreadPrice;
            pendingBuyTf = -1;
           }
        }

      //================= SELL SIDE =================
      if(trendDown && bullishCandle && c > bbUpper)
        {
         pendingSellTf = tf;
        }
      else if(pendingSellTf >= 0)
        {
         int barsElapsed = pendingSellTf - tf;
         if(barsElapsed > InpWaitBars)
           {
            pendingSellTf = -1;
           }
         else if(trendDown && bearishCandle && c < bbUpper)
           {
            tfType[tf] = -1;
            tfSL[tf]   = HighestHighFrom(tf) + InpSpreadMultiplier * spreadPrice;
            pendingSellTf = -1;
           }
        }
     }

   //--- alert hanya untuk tf-bar terbaru (tf==0), sekali per tf-bar
   if(tfType[0] == 1 && lastBuyAlertTfTime != iTime(Symbol(), InpTimeframe, 0))
     {
      lastBuyAlertTfTime = iTime(Symbol(), InpTimeframe, 0);
      string msg = StringFormat("%s %s BUY signal @ %s | SL=%s", Symbol(), EnumToString(InpTimeframe),
                                 DoubleToString(iClose(Symbol(), InpTimeframe, 0), Digits), DoubleToString(tfSL[0], Digits));
      if(EnableAlert) Alert(msg);
      if(EnablePushNotify) SendNotification(msg);
     }
   if(tfType[0] == -1 && lastSellAlertTfTime != iTime(Symbol(), InpTimeframe, 0))
     {
      lastSellAlertTfTime = iTime(Symbol(), InpTimeframe, 0);
      string msg = StringFormat("%s %s SELL signal @ %s | SL=%s", Symbol(), EnumToString(InpTimeframe),
                                 DoubleToString(iClose(Symbol(), InpTimeframe, 0), Digits), DoubleToString(tfSL[0], Digits));
      if(EnableAlert) Alert(msg);
      if(EnablePushNotify) SendNotification(msg);
     }

   //--- 2) Petakan hasil timeframe target ke bar-bar chart saat ini (mendukung chart TF berbeda dari InpTimeframe)
   int limit = rates_total - prev_calculated;
   if(prev_calculated == 0)
      limit = rates_total - 1;
   if(limit >= rates_total)
      limit = rates_total - 1;
   if(limit < 0)
      limit = 0;

   int prevTfShift = -999;
   for(int i = limit; i >= 0; i--)
     {
      int tfShift = iBarShift(Symbol(), InpTimeframe, time[i], false);
      if(tfShift < 0 || tfShift > tfProcessCount)
        {
         EmaFastBuf[i] = EMPTY_VALUE;
         EmaSlowBuf[i] = EMPTY_VALUE;
         BBUpperBuf[i] = EMPTY_VALUE;
         BBLowerBuf[i] = EMPTY_VALUE;
         BBMidBuf[i]   = EMPTY_VALUE;
         BuyArrowBuf[i]  = EMPTY_VALUE;
         SellArrowBuf[i] = EMPTY_VALUE;
         continue;
        }

      EmaFastBuf[i] = iMA(Symbol(), InpTimeframe, InpEmaFastPeriod, 0, MODE_EMA, PRICE_CLOSE, tfShift);
      EmaSlowBuf[i] = iMA(Symbol(), InpTimeframe, InpEmaSlowPeriod, 0, MODE_EMA, PRICE_CLOSE, tfShift);
      BBUpperBuf[i] = iBands(Symbol(), InpTimeframe, InpBBPeriod, InpBBDeviation, 0, PRICE_CLOSE, MODE_UPPER, tfShift);
      BBLowerBuf[i] = iBands(Symbol(), InpTimeframe, InpBBPeriod, InpBBDeviation, 0, PRICE_CLOSE, MODE_LOWER, tfShift);
      BBMidBuf[i]   = iBands(Symbol(), InpTimeframe, InpBBPeriod, InpBBDeviation, 0, PRICE_CLOSE, MODE_MAIN,  tfShift);
      BuyArrowBuf[i]  = EMPTY_VALUE;
      SellArrowBuf[i] = EMPTY_VALUE;

      // Anchor bar = bar chart pertama (dari lama ke baru) yang mewakili tf-bar ini -> tempat gambar panah
      bool isAnchor = (tfShift != prevTfShift);
      prevTfShift = tfShift;

      if(isAnchor && tfType[tfShift] == 1)
        {
         BuyArrowBuf[i] = low[i] - 3 * Point;
         DrawSLLine("MaduOKU_SL_BUY_" + TimeToString(iTime(Symbol(), InpTimeframe, tfShift)),
                    time[i], tfSL[tfShift], clrLime);
        }
      else if(isAnchor && tfType[tfShift] == -1)
        {
         SellArrowBuf[i] = high[i] + 3 * Point;
         DrawSLLine("MaduOKU_SL_SELL_" + TimeToString(iTime(Symbol(), InpTimeframe, tfShift)),
                    time[i], tfSL[tfShift], clrRed);
        }
     }

   return(rates_total);
  }
