# قرارداد سرویس و اصلاح سند اولیه

بررسی در ۱۲ نوامبر ۲۰۲۶ بر اساس صفحات و نمونه‌های عمومی رسمی BrsApi انجام شده است؛ نتیجه آزمون مجاز کلید حساب در LIVE_VALIDATION_FA.md آمده است.

| نام داخلی | مسیر منبع | پارامترهای لازم بجز key | اختیاری |
|---|---|---|---|
| symbols | Tsetmc/AllSymbols.php | — | type: 1..5 |
| indices | Tsetmc/Index.php | type: 1..3 | — |
| symbol | Tsetmc/Symbol.php | l18 | — |
| nav | Tsetmc/Nav.php | l18 | — |
| options | Tsetmc/Option.php | — | — |
| transactions | Tsetmc/Transaction.php | l18 | date؛ در برنامه ما صریحاً لازم است |
| history | Tsetmc/History.php | l18, type: 0/1 | — |
| candles | Tsetmc/Candlestick.php | l18, type: 1/2/3 | — |
| shareholders | Tsetmc/Shareholder.php | l18 | date |
| codal | Codal/Announcement.php | — | l18, category, period, audited, unaudited, only_main_company, only_subsidiaries, date_start, date_end, page |
| ime_futures | IME/Futures.php | — | — |
| ime_options | IME/Option.php | — | — |
| ime_certificates | IME/Certificate.php | — | — |
| ime_funds | IME/Fund.php | — | — |
| ime_physical | IME/Physical.php | — | date_start, date_end |
| commodities | Market/Commodity.php | — | — |

تاریخ‌ها هنگام ارسال، شمسی با ارقام لاتین و خط تیره هستند. پارامتر ناشناخته رد می‌شود؛ برای History پارامتر بازه تاریخ اختراع نشده و فیلتر تاریخ روی داده ذخیره‌شده اعمال می‌شود. `count` کندل، فیلد پاسخ است و به‌عنوان پارامتر ورودی تعریف نشده است.

تفاوت‌های اصلی با متن اولیه: مسیر کامودیتی Commodity است؛ NAV برای یک نماد درخواست می‌شود؛ ریزمعاملات تاریخ اختیاری دارد ولی روز آخر معامله را برمی‌گرداند؛ اطلاعیه‌های کدال در آرایه announcement همراه count_page هستند؛ کندل‌ها در candle_intraday/candle_daily و IME در برخی سرویس‌ها در data قرار دارند. نبود تاریخ در نمونه لحظه‌ای به دریافت زمینه از Symbol منجر شده است.

مدل پیشنهادی تراکنش، نوع خریدار و فروشنده را شامل می‌شد، ولی این فیلدها در قرارداد Transaction مستند نیستند و در کد حدس زده نمی‌شوند. واحد مقدار tval در IME می‌تواند هزار ریال باشد؛ واحد همراه داده حفظ می‌شود. پاسخ‌های option بورس کالا ممکن است برای call و put هم‌زمان فیلد داشته باشند و در ذخیره ساختاریافته به دو قرارداد تقسیم شده‌اند.

## منابع رسمی

- [AllSymbols](https://brsapi.ir/)
- [Index](https://brsapi.ir/bourse-api-index-webservice/)
- [Symbol](https://brsapi.ir/bourse-api-symbol-webservice/)
- [NAV](https://brsapi.ir/bourse-api-etf-funds-nav-webservice/)
- [Options](https://brsapi.ir/bourse-api-option-webservice/)
- [Transaction](https://brsapi.ir/bourse-api-transaction-webservice/)
- [History](https://brsapi.ir/bourse-api-history-webservice/)
- [Candlestick](https://brsapi.ir/bourse-api-candlestick-webservice/)
- [Shareholder](https://brsapi.ir/bourse-api-shareholder-webservice/)
- [Codal](https://brsapi.ir/bourse-api-codal-webservice/)
- [IME Futures](https://brsapi.ir/ime-api-futures-webservice/)
- [IME Options](https://brsapi.ir/ime-api-option-webservice/)
- [IME Certificate](https://brsapi.ir/ime-api-certificate-webservice/)
- [IME Fund](https://brsapi.ir/ime-api-fund-webservice/)
- [IME Physical](https://brsapi.ir/ime-api-physical-webservice/)
- [Commodity](https://brsapi.ir/free-api-commodity-webservice/)
