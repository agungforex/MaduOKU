# MaduOKU

Indikator scalping M1 untuk MetaTrader 4 (MQL4).

## MaduOKU Scalping M1

File: `MQL4/Indicators/MaduOKU_Scalping_M1.mq4`

Indikator custom timeframe M1 berbasis EMA74, EMA200, dan Bollinger Bands (20, 2)
dengan 3 tahap state machine:

1. **State 1 (filter tren)**
   - BUY bias: EMA74 di atas EMA200
   - SELL bias: EMA74 di bawah EMA200
2. **State 2 (candle ekstrem)**
   - BUY: candle bearish yang close di bawah BB bawah
   - SELL: candle bullish yang close di atas BB atas
   - State ini menunggu konfirmasi selama `InpWaitBars` candle (default 5), setelah itu invalid jika belum ada konfirmasi.
3. **State 3 (konfirmasi = sinyal)**
   - BUY: candle bullish berikutnya close kembali di atas BB bawah → panah BUY (hijau) di bawah candle
   - SELL: candle bearish berikutnya close kembali di bawah BB atas → panah SELL (merah) di atas candle

### Stop Loss

- SL BUY = Low terendah dari `InpSLLookback` candle terakhir (default 20) − (`InpSpreadMultiplier` × spread saat ini)
- SL SELL = High tertinggi dari `InpSLLookback` candle terakhir (default 20) + (`InpSpreadMultiplier` × spread saat ini)

Level SL digambar otomatis sebagai garis horizontal putus-putus di chart saat sinyal muncul.

### Input

| Input | Default | Keterangan |
|---|---|---|
| InpTimeframe | PERIOD_M1 | Timeframe data yang dibaca indikator (boleh beda dari timeframe chart tempat indikator dipasang) |
| InpEmaFastPeriod | 74 | Periode EMA cepat |
| InpEmaSlowPeriod | 200 | Periode EMA lambat |
| InpBBPeriod | 20 | Periode Bollinger Bands |
| InpBBDeviation | 2.0 | Deviasi Bollinger Bands |
| InpWaitBars | 5 | Window candle menunggu konfirmasi State3 |
| InpSLLookback | 20 | Jumlah candle untuk hitung Low/High terjauh (SL) |
| InpSpreadMultiplier | 2.0 | Kelipatan spread ditambahkan sebagai buffer SL |
| InpMaxTfBars | 3000 | Batas maksimal candle timeframe target yang diproses (performa) |
| ShowEmaBB | true | Tampilkan garis EMA & BB |
| ShowSLLines | true | Gambar garis SL saat sinyal muncul |
| EnableAlert | true | Alert popup MT4 saat sinyal baru |
| EnablePushNotify | false | Push notification ke HP (perlu setup MT4 push notification) |

### Instalasi

1. Copy `MaduOKU_Scalping_M1.mq4` ke folder `MQL4/Indicators/` pada data folder terminal MT4.
2. Restart MT4 atau refresh Navigator, lalu drag indikator ke chart.
3. Indikator membaca data sesuai `InpTimeframe` (default M1), terlepas dari timeframe chart tempat ia dipasang. Untuk penggunaan normal, tetap disarankan pasang di chart M1 dengan `InpTimeframe = PERIOD_M1`.
