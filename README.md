# MaduOKU — Early Warning Reversal Scanner

Sistem deteksi sinyal pembalikan tren (reversal) dini untuk **Gold (XAUUSD)**
dan **Bitcoin**, berbasis confluence dari beberapa indikator teknikal.

## Cara kerja

1. **Fetch data** OHLCV dari salah satu sumber (dipilih via `data_source` di config):
   - `binance_futures` (default) — histori kline dari Binance USDⓈ-M Futures public API,
     tanpa API key. `BTCUSDT` untuk bitcoin, `PAXGUSDT` (PAX Gold, mengikuti harga
     spot emas) sebagai proxy gold karena Binance tidak punya kontrak XAUUSD langsung.
   - `yfinance` — `GC=F` (gold futures) dan `BTC-USD`.
2. **Hitung indikator**: RSI, MACD histogram, ADX.
3. **Deteksi divergence** antara harga dan RSI/MACD di swing high/low terakhir:
   - *Regular bullish/bearish* → sinyal pembalikan (early warning).
   - *Hidden bullish/bearish* → sinyal lanjutan tren (dilaporkan, tidak menambah skor).
4. **Deteksi liquidity sweep** (Smart Money Concepts): harga menembus swing high/low
   `lookback` bar terakhir lalu ditutup kembali di dalam range — tanda stop order
   "disapu" sebelum reversal.
5. **Filter korelasi makro** (opsional): tren DXY/VIX terbaru diterjemahkan jadi
   bias bullish/bearish untuk simbol yang berkorelasi (mis. DXY naik → bearish
   untuk gold, VIX naik → risk-off yang mendukung gold & menekan bitcoin).
   Selalu diambil via `yfinance` karena tidak tersedia di Binance Futures.
6. **Klasifikasi regime** pasar (trending vs ranging) via ADX — reversal di pasar
   ranging dianggap lebih andal.
7. **Scoring confluence**: gabungkan semua bukti (divergence + sweep + makro)
   jadi satu skor. Alert hanya dikirim jika skor ≥ `min_score_to_alert`.
8. **Alert** opsional ke Telegram.

## Instalasi

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e . -r requirements-dev.txt
cp .env.example .env   # isi TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID jika perlu
```

## Menjalankan

```bash
python -m maduoku.main --config config.example.yaml
python -m maduoku.main --config config.example.yaml --telegram   # kirim alert
```

Konfigurasi (interval, periode indikator, threshold) ada di `config.example.yaml`
— salin ke `config.yaml` sendiri dan sesuaikan.

### Backtest

Validasi seberapa akurat sinyal reversal secara historis sebelum dipakai live.
Engine ini berjalan walk-forward (hanya memakai data yang "diketahui" sampai
bar tersebut, tanpa lookahead) dan mengukur return N bar ke depan setiap kali
sinyal actionable muncul:

```bash
python -m maduoku.backtest_main --config config.example.yaml --symbol bitcoin --forward-bars 5
python -m maduoku.backtest_main --config config.example.yaml --symbol gold --forward-bars 10 --step 2
```

Output: jumlah sinyal, win rate keseluruhan, rata-rata return per sinyal, dan
breakdown per arah (bullish/bearish).

### Parameter sweep

Cari kombinasi threshold (ADX, lookback liquidity sweep, min_score, dll) yang
paling baik performanya, dengan menjalankan backtest untuk setiap kombinasi
parameter di `sweep.example.yaml`:

```bash
python -m maduoku.sweep_main --config config.example.yaml --grid sweep.example.yaml --symbol bitcoin
python -m maduoku.sweep_main --grid sweep.example.yaml --symbol gold --min-signals 10 --out results.csv
```

Kombinasi dengan sinyal lebih sedikit dari `--min-signals` dibuang (biar tidak
tertipu win rate tinggi dari cuma 2 sinyal kebetulan). Hasil diurutkan dari
rata-rata return tertinggi.

> **Catatan**: filter korelasi makro belum masuk ke dalam backtest/sweep —
> keduanya hanya mensimulasikan divergence + liquidity sweep + regime ADX.
> Live scan (`main`) sudah menyertakan filter makro sepenuhnya.

## Testing

```bash
pytest -q
```

## Struktur project

```
src/maduoku/
  config.py            # load YAML config
  data/
    fetcher.py           # ambil OHLCV via yfinance
    binance_futures.py    # ambil OHLCV via Binance Futures public API
  indicators/           # RSI, MACD, ADX
  signals/
    pivots.py           # deteksi swing high/low (fractal)
    divergence.py        # regular & hidden divergence
    liquidity_sweep.py    # deteksi stop-hunt / liquidity sweep
    macro.py              # bias bullish/bearish dari tren DXY/VIX
    regime.py            # trending vs ranging (ADX)
    scoring.py           # confluence scoring -> EarlyWarning
  alerts/telegram.py     # kirim alert
  backtest/
    engine.py             # walk-forward backtest + summary stats
    sweep.py               # grid search parameter terbaik di atas engine
  main.py                # CLI entrypoint (live scan)
  backtest_main.py        # CLI entrypoint (backtest)
  sweep_main.py           # CLI entrypoint (parameter sweep)
tests/                   # unit test untuk divergence, scoring, data, backtest, sweep
```

## Roadmap pengembangan lanjutan

- Sertakan filter korelasi makro ke dalam backtest/sweep (perlu menyelaraskan
  histori DXY/VIX per-timestamp dengan simbol utama secara walk-forward).
- Funding rate / open interest Binance sebagai konfirmasi tambahan untuk bitcoin.
- Market regime detection yang lebih canggih (HMM) sebagai pengganti/pelengkap ADX.
