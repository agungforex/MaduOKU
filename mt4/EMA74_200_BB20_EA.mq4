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
input int              SwingLookback   = 24;   // jumlah candle ke belakang untuk cari swing high/low SL
input bool             CloseOnOppositeSignal = true; // Close posisi jika ada signal berlawanan (hanya saat floating profit > 0)
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
   int ticket, type;
   bool hasPosition = HasOpenPosition(ticket, type);
   string posText = hasPosition ? (type == OP_BUY ? "BUY open" : "SELL open") : "Tidak ada posisi";

   string text = "";
   text += "=== EMA74/200 + BB20 EA ===\n";
   text += "Breakout BB20 + slope EMA74 : " + (EnableSignal1 ? "true" : "false") + "\n";
   text += "Cross BB20 basis + slope basis/EMA74 : " + (EnableSignal2 ? "true" : "false") + "\n";
   text += "TradeMode : " + TradeModeToString() + "\n";
   text += "TF yang dibaca EA, independen dari chart : " + EnumToString(ActiveTimeframe) + "\n";
   text += "LotSize : " + DoubleToString(LotSize, 2) + "\n";
   text += "Close on opposite signal (jika profit) : " + (CloseOnOppositeSignal ? "true" : "false") + "\n";
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
   return swingLow - MarketInfo(Symbol(), MODE_SPREAD) * Point;
}

double SwingHighSL()
{
   int idx = iHighest(NULL, ActiveTimeframe, MODE_HIGH, SwingLookback, 1);
   double swingHigh = iHigh(NULL, ActiveTimeframe, idx);
   return swingHigh + MarketInfo(Symbol(), MODE_SPREAD) * Point;
}

bool IsFloatingProfit(int ticket)
{
   if(!OrderSelect(ticket, SELECT_BY_TICKET))
      return false;
   double floating = OrderProfit() + OrderSwap() + OrderCommission();
   return floating > 0;
}

bool HasOpenPosition(int &ticket, int &type)
{
   for(int i = 0; i < OrdersTotal(); i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderSymbol() != Symbol() || OrderMagicNumber() != MagicNumber) continue;
      if(OrderType() == OP_BUY || OrderType() == OP_SELL)
      {
         ticket = OrderTicket();
         type = OrderType();
         return true;
      }
   }
   return false;
}

void ClosePosition(int ticket, int type)
{
   double price = (type == OP_BUY) ? Bid : Ask;
   if(!OrderClose(ticket, LotSize, price, Slippage, clrYellow))
      Print("OrderClose gagal, ticket=", ticket, " error=", GetLastError());
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

   bool buySignal  = (TradeMode == BUY_ONLY  || TradeMode == BOTH) && CheckBuySignal();
   bool sellSignal = (TradeMode == SELL_ONLY || TradeMode == BOTH) && CheckSellSignal();

   int ticket, type;
   bool hasPosition = HasOpenPosition(ticket, type);

   if(hasPosition)
   {
      bool oppositeSignal = (type == OP_BUY && sellSignal) || (type == OP_SELL && buySignal);

      if(CloseOnOppositeSignal && oppositeSignal && IsFloatingProfit(ticket))
      {
         ClosePosition(ticket, type);
         hasPosition = false;
      }
      else
      {
         return; // posisi searah, sinyal berlawanan saat floating loss, atau fitur close nonaktif
      }
   }

   if(!hasPosition)
   {
      if(buySignal)
         OpenBuy();
      else if(sellSignal)
         OpenSell();
   }
}
