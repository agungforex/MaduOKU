# MaduOKU — Early Warning Reversal Scanner

Sistem deteksi sinyal pembalikan tren (reversal) dini untuk **Gold (XAUUSD)**
dan **Bitcoin**, berbasis confluence dari beberapa indikator teknikal.

## Cara kerja

1. **Fetch data** OHLCV via `yfinance` (`GC=F` untuk gold, `BTC-USD` untuk bitcoin).
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

## Testing

```bash
pytest -q
```

## Struktur project

```
src/maduoku/
  config.py            # load YAML config
  data/fetcher.py       # ambil OHLCV via yfinance
  indicators/           # RSI, MACD, ADX
  signals/
    pivots.py           # deteksi swing high/low (fractal)
    divergence.py        # regular & hidden divergence
    regime.py            # trending vs ranging (ADX)
    scoring.py           # confluence scoring -> EarlyWarning
  alerts/telegram.py     # kirim alert
  main.py                # CLI entrypoint
tests/                   # unit test untuk divergence & scoring
```

## Roadmap pengembangan lanjutan

- Liquidity sweep / stop-hunt detection (ala Smart Money Concepts) sebagai
  konfirmasi tambahan sebelum reversal.
- Filter korelasi makro (DXY, VIX) untuk gold; funding rate/open interest
  untuk bitcoin.
- Backtesting engine untuk validasi win-rate tiap kombinasi sinyal.
- Market regime detection yang lebih canggih (HMM) sebagai pengganti/pelengkap ADX.
