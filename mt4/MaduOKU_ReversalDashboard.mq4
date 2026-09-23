#property copyright "MaduOKU"
#property strict
#property indicator_chart_window
#property indicator_plots 0

//--- inputs
input string            InpSymbolOverride  = "";                 // Override symbol name (blank = use chart symbol)
input string            InpSignalSubfolder = "MaduOKU_Signals";  // Subfolder inside MT4's Common\Files
input int               InpRefreshSeconds  = 5;                  // Refresh interval (seconds)
input int               InpFontSize        = 9;                  // Font size
input color             InpBullishColor    = clrLimeGreen;
input color             InpBearishColor    = clrTomato;
input color             InpNoneColor       = clrSilver;
input color             InpStaleColor      = clrOrange;
input ENUM_BASE_CORNER  InpCorner          = CORNER_LEFT_UPPER;
input int               InpXOffset         = 10;
input int               InpYOffset         = 20;

// Timeframes the Python pipeline was trained on (minutes), and their display labels.
int    g_tf_minutes[4] = {5, 15, 60, 240};
string g_tf_labels[4]  = {"M5", "M15", "H1", "H4"};

string g_prefix = "MaduOKU_Dash_";
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
   CreateLabel(g_prefix + "Title", g_symbol + " - Reversal Watch", InpXOffset, InpYOffset, InpFontSize + 2, clrWhite);
   for(int i = 0; i < 4; i++)
   {
      int y = InpYOffset + (i + 1) * rowHeight;
      CreateLabel(g_prefix + "TF_" + g_tf_labels[i], g_tf_labels[i] + ":", InpXOffset, y, InpFontSize, clrSilver);
      CreateLabel(g_prefix + "Sig_" + g_tf_labels[i], "loading...", InpXOffset + 45, y, InpFontSize, clrSilver);
   }
   CreateLabel(g_prefix + "Updated", "", InpXOffset, InpYOffset + 5 * rowHeight, InpFontSize - 1, clrGray);
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
   datetime latest = 0;
   for(int i = 0; i < 4; i++)
   {
      string file = g_symbol + IntegerToString(g_tf_minutes[i]) + ".csv";
      string path = InpSignalSubfolder + "\\" + file;

      datetime ts;
      string signal;
      double probNone, probBull, probBear;
      bool ok = ReadSignalFile(path, ts, signal, probNone, probBull, probBear);

      string labelName = g_prefix + "Sig_" + g_tf_labels[i];
      if(!ok)
      {
         ObjectSetString(0, labelName, OBJPROP_TEXT, "no data");
         ObjectSetInteger(0, labelName, OBJPROP_COLOR, clrGray);
         continue;
      }

      if(ts > latest) latest = ts;

      double confidence = (signal == "none") ? probNone : MathMax(probBull, probBear);
      bool stale = (TimeCurrent() - ts) > g_tf_minutes[i] * 60 * 3;

      color  clr;
      string display;
      if(stale)
      {
         clr = InpStaleColor;
         display = StringFormat("%s (%.0f%%) [STALE]", signal, confidence * 100);
      }
      else if(signal == "bullish_reversal")
      {
         clr = InpBullishColor;
         display = StringFormat("BULLISH (%.0f%%)", confidence * 100);
      }
      else if(signal == "bearish_reversal")
      {
         clr = InpBearishColor;
         display = StringFormat("BEARISH (%.0f%%)", confidence * 100);
      }
      else
      {
         clr = InpNoneColor;
         display = StringFormat("none (%.0f%%)", confidence * 100);
      }

      ObjectSetString(0, labelName, OBJPROP_TEXT, display);
      ObjectSetInteger(0, labelName, OBJPROP_COLOR, clr);
   }

   if(latest > 0)
      ObjectSetString(0, g_prefix + "Updated", OBJPROP_TEXT, "Last data: " + TimeToString(latest, TIME_DATE | TIME_MINUTES));
}

// Reads a signal file written by scripts/export_mt4_signal.py:
// one line "yyyy.mm.dd hh:mi,signal,prob_none,prob_bullish,prob_bearish"
bool ReadSignalFile(string path, datetime &ts, string &signal, double &probNone, double &probBull, double &probBear)
{
   int handle = FileOpen(path, FILE_READ | FILE_CSV | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE, ',');
   if(handle == INVALID_HANDLE)
      return(false);

   string cols[5];
   bool found = false;
   while(!FileIsEnding(handle))
   {
      string col0 = FileReadString(handle);
      if(col0 == "") break;
      cols[0] = col0;
      cols[1] = FileReadString(handle);
      cols[2] = FileReadString(handle);
      cols[3] = FileReadString(handle);
      cols[4] = FileReadString(handle);
      found = true;
   }
   FileClose(handle);

   if(!found) return(false);

   ts       = StringToTime(cols[0]);
   signal   = cols[1];
   probNone = StringToDouble(cols[2]);
   probBull = StringToDouble(cols[3]);
   probBear = StringToDouble(cols[4]);
   return(true);
}
