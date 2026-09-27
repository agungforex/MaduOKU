#property copyright "MaduOKU"
#property strict

enum ENUM_TRADE_MODE
{
   BUY_ONLY  = 0,
   SELL_ONLY = 1,
   BOTH      = 2
};

input int              EmaFastPeriod   = 74;
input int              EmaSlowPeriod   = 200;
input int              BBPeriod        = 20;
input double           BBDeviation     = 2.0;

input bool             EnableSignal1   = true;   // Breakout BB20 + slope EMA74
input bool             EnableSignal2   = true;   // Cross BB20 basis + slope basis/EMA74

input ENUM_TRADE_MODE  TradeMode       = BOTH;
input ENUM_TIMEFRAMES  ActiveTimeframe = PERIOD_M15; // TF yang dibaca EA, independen dari chart

input double           LotSize         = 0.01;
input int              MaxPositions    = 1;     // Maksimal posisi searah yang boleh terbuka bersamaan
input int              SwingLookback   = 24;   // jumlah candle ke belakang untuk cari swing high/low SL
input bool             CloseOnOppositeSignal = true; // Close semua posisi jika ada signal berlawanan (hanya saat total floating profit > 0)
input bool             RequireBOS      = true;  // Signal valid hanya jika searah BOS terakhir
input int              BosLookback     = 50;    // BOS harus terjadi dalam N candle terakhir
input int              MagicNumber     = 74200;
input int              Slippage        = 5;

datetime lastBarTime = 0;

int OnInit()
{
   ShowPanel();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   Comment("");
}

string TradeModeToString()
{
   if(TradeMode == BUY_ONLY)  return "BUY ONLY";
   if(TradeMode == SELL_ONLY) return "SELL ONLY";
   return "BOTH";
}

void ShowPanel()
{
   int type;
   double totalFloating;
   int count = CountOpenPositions(type, totalFloating);
   string posText = count == 0 ? "Tidak ada posisi" : (type == OP_BUY ? "BUY" : "SELL") + " x" + IntegerToString(count) + "/" + IntegerToString(MaxPositions);

   string text = "";
   text += "=== EMA74/200 + BB20 EA ===\n";
   text += "Breakout BB20 + slope EMA74 : " + (EnableSignal1 ? "true" : "false") + "\n";
   text += "Cross BB20 basis + slope basis/EMA74 : " + (EnableSignal2 ? "true" : "false") + "\n";
   text += "TradeMode : " + TradeModeToString() + "\n";
   text += "TF yang dibaca EA, independen dari chart : " + EnumToString(ActiveTimeframe) + "\n";
   text += "LotSize : " + DoubleToString(LotSize, 2) + "\n";
   text += "MaxPositions : " + IntegerToString(MaxPositions) + "\n";
   text += "Close on opposite signal (jika profit) : " + (CloseOnOppositeSignal ? "true" : "false") + "\n";
   text += "Wajib searah BOS (N=" + IntegerToString(BosLookback) + ") : " + (RequireBOS ? "true" : "false") + "\n";
   text += "Posisi : " + posText;

   Comment(text);
}

double EmaFastAt(int shift)
{
   return iMA(NULL, ActiveTimeframe, EmaFastPeriod, 0, MODE_EMA, PRICE_CLOSE, shift);
}

double BasisAt(int shift)
{
   return iBands(NULL, ActiveTimeframe, BBPeriod, BBDeviation, 0, PRICE_CLOSE, MODE_MAIN, shift);
}

double UpperAt(int shift)
{
   return iBands(NULL, ActiveTimeframe, BBPeriod, BBDeviation, 0, PRICE_CLOSE, MODE_UPPER, shift);
}

double LowerAt(int shift)
{
   return iBands(NULL, ActiveTimeframe, BBPeriod, BBDeviation, 0, PRICE_CLOSE, MODE_LOWER, shift);
}

double CloseAt(int shift)
{
   return iClose(NULL, ActiveTimeframe, shift);
}

// Cari BOS (Break of Structure) terakhir dalam N candle terakhir.
// Swing high/low pakai fractal 5-bar bawaan MT4 (iFractals), validasi pakai close candle.
// Return: 1 = BOS bullish terakhir, -1 = BOS bearish terakhir, 0 = tidak ada BOS dalam lookback.
int GetBOSDirection(int lookback)
{
   double swingHigh = -1.0;
   double swingLow  = -1.0;
   int    lastBOS    = 0;

   int scanStart = lookback + 20; // bar tambahan untuk cari swing awal sebelum window lookback dimulai

   for(int s = scanStart; s >= 3; s--)
   {
      double fh = iFractals(NULL, ActiveTimeframe, MODE_UPPER, s);
      double fl = iFractals(NULL, ActiveTimeframe, MODE_LOWER, s);
      if(fh != 0.0) swingHigh = fh;
      if(fl != 0.0) swingLow  = fl;

      if(s <= lookback)
      {
         double closeAtS = iClose(NULL, ActiveTimeframe, s);
         if(swingHigh > 0 && closeAtS > swingHigh)
         {
            lastBOS = 1;
            swingHigh = -1.0; // tunggu fractal baru sebelum BOS bullish berikutnya bisa terdeteksi lagi
         }
         else if(swingLow > 0 && closeAtS < swingLow)
         {
            lastBOS = -1;
            swingLow = -1.0;
         }
      }
   }

   return lastBOS;
}

// shift 1 = candle terakhir yang sudah closed (dievaluasi sebagai "candle sekarang" untuk sinyal)
bool CheckBuySignal()
{
   double emaFastNow  = EmaFastAt(1);
   double emaFastPrev = EmaFastAt(2);
   bool   emaFastUp   = emaFastNow > emaFastPrev;

   if(EnableSignal1)
   {
      double upperNow  = UpperAt(1);
      double upperPrev = UpperAt(2);
      bool breakoutUp = CloseAt(1) > upperNow && CloseAt(2) <= upperPrev;
      if(breakoutUp && emaFastUp)
         return true;
   }

   if(EnableSignal2)
   {
      double basisNow  = BasisAt(1);
      double basisPrev = BasisAt(2);
      bool basisUp = basisNow > basisPrev;
      bool crossBasisUp = CloseAt(1) > basisNow && CloseAt(2) <= basisPrev;
      if(crossBasisUp && (basisUp || emaFastUp))
         return true;
   }

   return false;
}

bool CheckSellSignal()
{
   double emaFastNow  = EmaFastAt(1);
   double emaFastPrev = EmaFastAt(2);
   bool   emaFastDown = emaFastNow < emaFastPrev;

   if(EnableSignal1)
   {
      double lowerNow  = LowerAt(1);
      double lowerPrev = LowerAt(2);
      bool breakoutDown = CloseAt(1) < lowerNow && CloseAt(2) >= lowerPrev;
      if(breakoutDown && emaFastDown)
         return true;
   }

   if(EnableSignal2)
   {
      double basisNow  = BasisAt(1);
      double basisPrev = BasisAt(2);
      bool basisDown = basisNow < basisPrev;
      bool crossBasisDown = CloseAt(1) < basisNow && CloseAt(2) >= basisPrev;
      if(crossBasisDown && (basisDown || emaFastDown))
         return true;
   }

   return false;
}

double SwingLowSL()
{
   int idx = iLowest(NULL, ActiveTimeframe, MODE_LOW, SwingLookback, 1);
   double swingLow = iLow(NULL, ActiveTimeframe, idx);
   return swingLow - 2 * MarketInfo(Symbol(), MODE_SPREAD) * Point;
}

double SwingHighSL()
{
   int idx = iHighest(NULL, ActiveTimeframe, MODE_HIGH, SwingLookback, 1);
   double swingHigh = iHigh(NULL, ActiveTimeframe, idx);
   return swingHigh + 2 * MarketInfo(Symbol(), MODE_SPREAD) * Point;
}

// Hitung semua posisi EA ini yang masih terbuka (harusnya selalu searah, karena entry baru
// selalu mengikuti arah posisi yang sudah ada). type diisi arah posisi (OP_BUY/OP_SELL) kalau count>0.
int CountOpenPositions(int &type, double &totalFloating)
{
   int count = 0;
   type = -1;
   totalFloating = 0.0;

   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderSymbol() != Symbol() || OrderMagicNumber() != MagicNumber) continue;
      if(OrderType() != OP_BUY && OrderType() != OP_SELL) continue;

      count++;
      type = OrderType();
      totalFloating += OrderProfit() + OrderSwap() + OrderCommission();
   }

   return count;
}

void CloseAllPositions(int type)
{
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderSymbol() != Symbol() || OrderMagicNumber() != MagicNumber) continue;
      if(OrderType() != type) continue;

      double price = (type == OP_BUY) ? Bid : Ask;
      if(!OrderClose(OrderTicket(), OrderLots(), price, Slippage, clrYellow))
         Print("OrderClose gagal, ticket=", OrderTicket(), " error=", GetLastError());
   }
}

void OpenBuy()
{
   double sl = SwingLowSL();
   if(OrderSend(Symbol(), OP_BUY, LotSize, Ask, Slippage, sl, 0, "EMA74/200 BB20 EA", MagicNumber, 0, clrGreen) < 0)
      Print("OrderSend BUY gagal, error=", GetLastError());
}

void OpenSell()
{
   double sl = SwingHighSL();
   if(OrderSend(Symbol(), OP_SELL, LotSize, Bid, Slippage, sl, 0, "EMA74/200 BB20 EA", MagicNumber, 0, clrRed) < 0)
      Print("OrderSend SELL gagal, error=", GetLastError());
}

void OnTick()
{
   ShowPanel();

   datetime currentBarTime = iTime(NULL, ActiveTimeframe, 0);
   if(currentBarTime == lastBarTime)
      return;
   lastBarTime = currentBarTime;

   // Raw signal dari indikator, TIDAK difilter TradeMode -> dipakai khusus untuk close posisi
   bool rawBuySignal  = CheckBuySignal();
   bool rawSellSignal = CheckSellSignal();

   if(RequireBOS)
   {
      int bosDir = GetBOSDirection(BosLookback);
      rawBuySignal  = rawBuySignal  && (bosDir == 1);
      rawSellSignal = rawSellSignal && (bosDir == -1);
   }

   // Signal untuk entry baru, difilter TradeMode (BUY_ONLY/SELL_ONLY/BOTH)
   bool buyEntrySignal  = (TradeMode == BUY_ONLY  || TradeMode == BOTH) && rawBuySignal;
   bool sellEntrySignal = (TradeMode == SELL_ONLY || TradeMode == BOTH) && rawSellSignal;

   int type;
   double totalFloating;
   int count = CountOpenPositions(type, totalFloating);

   if(count > 0)
   {
      // Close pakai raw signal, tidak peduli TradeMode. Floating dihitung dari total semua posisi.
      bool oppositeSignal = (type == OP_BUY && rawSellSignal) || (type == OP_SELL && rawBuySignal);

      if(CloseOnOppositeSignal && oppositeSignal && totalFloating > 0)
      {
         CloseAllPositions(type);
         count = 0;
      }
      else
      {
         // Sinyal berlawanan saat floating loss, atau fitur close nonaktif -> posisi tetap jalan.
         // Sinyal SEARAH boleh menambah posisi baru selama belum mencapai MaxPositions.
         bool sameDirectionSignal = (type == OP_BUY && buyEntrySignal) || (type == OP_SELL && sellEntrySignal);
         if(sameDirectionSignal && count < MaxPositions)
         {
            if(type == OP_BUY) OpenBuy(); else OpenSell();
         }
         return;
      }
   }

   if(count == 0)
   {
      // Posisi pertama (termasuk reverse setelah close) tetap ikut TradeMode
      if(buyEntrySignal)
         OpenBuy();
      else if(sellEntrySignal)
         OpenSell();
   }
}
