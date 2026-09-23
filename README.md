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
4. **Klasifikasi regime** pasar (trending vs ranging) via ADX — reversal di pasar
   ranging dianggap lebih andal.
5. **Scoring confluence**: gabungkan semua bukti jadi satu skor. Alert hanya
   dikirim jika skor ≥ `min_score_to_alert`.
6. **Alert** opsional ke Telegram.

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
    regime.py            # trending vs ranging (ADX)
    scoring.py           # confluence scoring -> EarlyWarning
  alerts/telegram.py     # kirim alert
  backtest/engine.py      # walk-forward backtest + summary stats
  main.py                # CLI entrypoint (live scan)
  backtest_main.py        # CLI entrypoint (backtest)
tests/                   # unit test untuk divergence, scoring, data, backtest
```

## Roadmap pengembangan lanjutan

- Liquidity sweep / stop-hunt detection (ala Smart Money Concepts) sebagai
  konfirmasi tambahan sebelum reversal.
- Filter korelasi makro (DXY, VIX) untuk gold; funding rate/open interest
  untuk bitcoin.
- Market regime detection yang lebih canggih (HMM) sebagai pengganti/pelengkap ADX.
- Parameter sweep otomatis di atas backtest engine untuk mencari kombinasi
  threshold (RSI/ADX/min_score) paling optimal per simbol.
