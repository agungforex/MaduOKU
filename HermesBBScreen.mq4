//+------------------------------------------------------------------+
//| HermesBBScreen.mq4 - READ-ONLY screener data exporter             |
//| Loop semua simbol Market Watch, hitung BB20(2.0) H4/D1/W1 live,   |
//| plus EMA74 dan status EMA74 di dalam/di luar BB.                 |
//| Tulis MQL4\Files\hermes_bbscreen.txt. Tidak ada order/modify.     |
//| Pasang di SATU chart mana saja.                                   |
//+------------------------------------------------------------------+
#property copyright "Hermes"
#property version   "1.10"
#property strict
#property indicator_chart_window

input int    BBPeriod   = 20;
input double BBDev      = 2.0;
input int    EMAPeriod  = 74;
input int    EverySec   = 5;
input bool   ShowPanel  = true;   // tampilkan panel di chart
input int    PanelX     = 10;
input int    PanelY     = 30;
input int    FontSize   = 9;
input int    PairsPerLine = 6;
input color  ColUp      = clrTomato;      // BB atas
input color  ColLo      = clrLimeGreen;   // BB bawah
input color  ColEma     = clrGold;        // EMA di dalam BB
input color  ColHead    = clrSilver;
string PFX = "HBBS_";
string FNAME = "hermes_bbscreen.txt";
string FTMP  = "hermes_bbscreen.tmp";
int    TFS[3] = {240, 1440, 10080};

int OnInit()
{
   EventSetTimer(EverySec);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ClearPanel();
}

void ClearPanel()
{
   for(int i = ObjectsTotal() - 1; i >= 0; i--)
   {
      string nm = ObjectName(i);
      if(StringFind(nm, PFX) == 0) ObjectDelete(nm);
   }
}

int rowY = 0;
void Lbl(string txt, color c)
{
   string nm = PFX + IntegerToString(rowY);
   if(ObjectFind(nm) < 0)
   {
      ObjectCreate(nm, OBJ_LABEL, 0, 0, 0);
      ObjectSet(nm, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSet(nm, OBJPROP_XDISTANCE, PanelX);
      ObjectSet(nm, OBJPROP_SELECTABLE, false);
   }
   ObjectSet(nm, OBJPROP_YDISTANCE, PanelY + rowY * (FontSize + 7));
   ObjectSetText(nm, txt, FontSize, "Consolas", c);
   rowY++;
}

void DrawRow(string title, string &list[], int cnt, color c)
{
   if(cnt == 0) { Lbl(title + " : -", c); return; }
   string line = title + " : ";
   int inLine = 0;
   string pad = "";
   for(int k = 0; k < StringLen(title) + 3; k++) pad += " ";
   for(int i = 0; i < cnt; i++)
   {
      line += list[i];
      inLine++;
      if(i < cnt - 1)
      {
         if(inLine >= PairsPerLine) { Lbl(line, c); line = pad; inLine = 0; }
         else line += ", ";
      }
   }
   Lbl(line, c);
}

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   return(rates_total);
}

void OnTimer()
{
   int h = FileOpen(FTMP, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   FileWriteString(h, "META|" + AccountServer() + "|" + IntegerToString((int)TimeCurrent()) + "|" +
                   IntegerToString((int)TimeLocal()) + "|" + IntegerToString(BBPeriod) + "|" +
                   DoubleToString(BBDev, 1) + "|" + IntegerToString(EMAPeriod) + "\n");
   string lst[6][40];
   int cnt[6] = {0,0,0,0,0,0};   // idx = tfIndex*2 + (0 atas,1 bawah)
   string lstP[6][40];           // candle sebelumnya (sudah close, shift 1)
   int cntP[6] = {0,0,0,0,0,0};
   string lstE[3][40];           // EMA74 di dalam BB, per TF (0=H4,1=D1,2=W1)
   int cntE[3] = {0,0,0};
   int n = SymbolsTotal(true);
   for(int i = 0; i < n; i++)
   {
      string s = SymbolName(i, true);
      double bid = MarketInfo(s, MODE_BID);
      int dg = (int)MarketInfo(s, MODE_DIGITS);
      datetime lt = (datetime)MarketInfo(s, MODE_TIME);
      for(int k = 0; k < 3; k++)
      {
         int tf = TFS[k];
         double up = iBands(s, tf, BBPeriod, BBDev, 0, PRICE_CLOSE, MODE_UPPER, 0);
         double md = iBands(s, tf, BBPeriod, BBDev, 0, PRICE_CLOSE, MODE_MAIN, 0);
         double lo = iBands(s, tf, BBPeriod, BBDev, 0, PRICE_CLOSE, MODE_LOWER, 0);
         double hi0 = iHigh(s, tf, 0);
         double lo0 = iLow(s, tf, 0);
         datetime bt = iTime(s, tf, 0);
         double ema = iMA(s, tf, EMAPeriod, 0, MODE_EMA, PRICE_CLOSE, 0);
         if(up <= 0 || lo <= 0 || hi0 <= 0 || bt == 0) continue;
         if(hi0 >= up && cnt[k*2] < 40)     { lst[k*2][cnt[k*2]] = s;     cnt[k*2]++; }
         if(lo0 <= lo && cnt[k*2+1] < 40)   { lst[k*2+1][cnt[k*2+1]] = s; cnt[k*2+1]++; }
         // screening EMA74 berada di dalam BB (antara lower dan upper)
         if(ema > 0 && ema >= lo && ema <= up && cntE[k] < 40)
         {
            lstE[k][cntE[k]] = s;
            cntE[k]++;
         }
         // candle sebelumnya yang sudah close (shift 1) dengan BB di bar itu
         double upP = iBands(s, tf, BBPeriod, BBDev, 0, PRICE_CLOSE, MODE_UPPER, 1);
         double loP = iBands(s, tf, BBPeriod, BBDev, 0, PRICE_CLOSE, MODE_LOWER, 1);
         double hi1 = iHigh(s, tf, 1);
         double lo1 = iLow(s, tf, 1);
         if(upP > 0 && loP > 0 && hi1 > 0)
         {
            if(hi1 >= upP && cntP[k*2] < 40)     { lstP[k*2][cntP[k*2]] = s;     cntP[k*2]++; }
            if(lo1 <= loP && cntP[k*2+1] < 40)   { lstP[k*2+1][cntP[k*2+1]] = s; cntP[k*2+1]++; }
         }
         FileWriteString(h, s + "|" + IntegerToString(tf) + "|" + DoubleToString(bid, dg) + "|" +
                         DoubleToString(hi0, dg) + "|" + DoubleToString(lo0, dg) + "|" +
                         DoubleToString(up, dg) + "|" + DoubleToString(md, dg) + "|" +
                         DoubleToString(lo, dg) + "|" + IntegerToString((int)bt) + "|" +
                         IntegerToString((int)lt) + "|" +
                         DoubleToString(hi1, dg) + "|" + DoubleToString(lo1, dg) + "|" +
                         DoubleToString(upP, dg) + "|" + DoubleToString(loP, dg) + "|" +
                         IntegerToString((int)iTime(s, tf, 1)) + "|" +
                         DoubleToString(ema, dg) + "\n");
      }
   }
   FileClose(h);
   FileMove(FTMP, 0, FNAME, FILE_REWRITE);

   if(ShowPanel)
   {
      rowY = 0;
      Lbl("SCREENER BB20 (" + IntegerToString(BBPeriod) + "," + DoubleToString(BBDev,1) + ") + EMA" +
          IntegerToString(EMAPeriod) + "  " + TimeToString(TimeCurrent(), TIME_MINUTES) + " server", ColHead);
      string a0[]; string a1[]; string a2[]; string a3[]; string a4[]; string a5[];
      ArrayResize(a0, 40); ArrayResize(a1, 40); ArrayResize(a2, 40);
      ArrayResize(a3, 40); ArrayResize(a4, 40); ArrayResize(a5, 40);
      for(int j = 0; j < 40; j++)
      {
         a0[j] = lst[0][j]; a1[j] = lst[1][j]; a2[j] = lst[2][j];
         a3[j] = lst[3][j]; a4[j] = lst[4][j]; a5[j] = lst[5][j];
      }
      DrawRow("H4 BB ATAS ", a0, cnt[0], ColUp);
      DrawRow("H4 BB BAWAH", a1, cnt[1], ColLo);
      DrawRow("D1 BB ATAS ", a2, cnt[2], ColUp);
      DrawRow("D1 BB BAWAH", a3, cnt[3], ColLo);
      DrawRow("W1 BB ATAS ", a4, cnt[4], ColUp);
      DrawRow("W1 BB BAWAH", a5, cnt[5], ColLo);

      // bagian EMA74 di dalam BB, per TF
      Lbl("", ColHead);
      Lbl("EMA" + IntegerToString(EMAPeriod) + " DI DALAM BB", ColHead);
      string etitle[3] = {"H4 EMA IN BB", "D1 EMA IN BB", "W1 EMA IN BB"};
      for(int qe = 0; qe < 3; qe++)
      {
         string el[]; ArrayResize(el, 40);
         for(int j3 = 0; j3 < 40; j3++) el[j3] = lstE[qe][j3];
         DrawRow(etitle[qe], el, cntE[qe], ColEma);
      }

      // bagian bawah: candle sebelumnya yang sudah close (H4, D1, W1)
      Lbl("", ColHead);
      Lbl("CANDLE SEBELUMNYA (sudah close) - high/low sentuh BB bar itu", ColHead);
      string pn[6] = {"H4 BB ATAS ", "H4 BB BAWAH", "D1 BB ATAS ", "D1 BB BAWAH", "W1 BB ATAS ", "W1 BB BAWAH"};
      for(int q = 0; q < 6; q++)
      {
         string pl[]; ArrayResize(pl, 40);
         for(int j2 = 0; j2 < 40; j2++) pl[j2] = lstP[q][j2];
         DrawRow(pn[q], pl, cntP[q], (q % 2 == 0) ? ColUp : ColLo);
      }
      // hapus sisa label lama bila baris berkurang
      for(int r = rowY; r < rowY + 30; r++)
         ObjectDelete(PFX + IntegerToString(r));
      ChartRedraw();
   }
}
