# شناخت بازار، یادگیری و ارزیابی - نسخه پژوهشی دوم

نتیجه اقتصادی نسخه فعلی پذیرفته نشده است. کد قابل اجرا و گزارش نهایی موجود است؛ ارسال سفارش و اتصال کارگزاری وجود ندارد. داشبورد تاریخی است. برای خواندن، از reports/01_MARKET_AND_PARTICIPANTS_FA.md شروع کنید و سپس گزارش یکپارچه results/final_report.html را ببینید.

## اجرا از ریشه مخزن

```bash
python -m pip install -r research_step2/requirements.txt
python research_step2/src/run.py --data Data
python research_step2/src/matched_stress.py --data Data
python -m unittest discover -s research_step2/tests -v
python -m unittest discover -s research_step1/tests -v
python research_step2/src/make_report.py
python -m http.server 8000
```

داشبورد: http://localhost:8000/research_step2/results/dashboard.html

گزارش کامل: http://localhost:8000/research_step2/results/final_report.html

مدل تطبیقی به بارگذار داده گام اول وابسته است؛ هر دو پوشه باید در مخزن باشند. آستانه‌ها و پیکربندی از config.json و قواعد صریح src/engine.py می‌آیند. آرشیو سهام قدیمی مستقل از آموزش صندوق‌هاست. اجرای مجددِ گزارش نیازمند خروجی‌های بررسی تاریخی است که در results همراه شده‌اند؛ اجرای دوباره خود آن تحلیل با دستورهای زیر ممکن است.

## بازتولید تحلیل آرشیو تاریخی خارجی، اختیاری

به علت احرازنشدن مجوز بازتوزیع داده خام خارجی، فایل‌ها همراه این پروژه منتشر نشده‌اند. منبع و commit و hash آن‌ها در external_sources.json ثبت است. اسکریپت دریافت به دسترسی مجاز اینترنت نیاز دارد؛ در این اجرا فایل‌ها از اتصال GitHub دریافت شدند و بایت‌هایشان تطبیق داده شد. دانلود HTTP اسکریپت در این محیط مستقلاً آزموده نشده است.

```bash
python research_step2/src/fetch_external.py --dest external_history
python research_step2/src/historical_behavior.py --input external_history
python research_step2/src/make_report.py
```

این آرشیو تا ۲۰۲۱ است و داده جاری سهام محسوب نمی‌شود. نگاشت نام فایل به نماد با candidate برچسب خورده است. تحلیل سالانه/ماهانه آن، فعالیت جمعی است و نه بازسازی مالکیت/هویت سهامدار.

## ورودی آینده ریزساختار

governance.py واردکننده فایل JSONL زمان‌دار است و ابزار دریافت زنده نیست. هر رکورد باید instrument_id، observed_at، exchange_timestamp، source، kind و payload داشته باشد. زمان باید timezone صریح داشته باشد؛ برای kind=book، عمق bids/asks، lower_limit، upper_limit و status لازم‌اند. آرشیو بازنویسی نمی‌شود. نمونه قالب صرفاً ساختار زیر است؛ داده واقعی نیست:

```json
{"instrument_id":"SOURCE_INSTRUMENT_ID","observed_at":"2026-11-12T12:01:00+03:30","exchange_timestamp":"2026-11-12T12:00:59+03:30","source":"VERIFIED_SOURCE","kind":"book","payload":{"bids":[{"price":100,"quantity":1000}],"asks":[{"price":101,"quantity":1000}],"lower_limit":90,"upper_limit":110,"status":"OPEN"}}
```

```bash
python research_step2/src/governance.py --input observations.jsonl --archive archive/session.jsonl
```

حتی مظنه زمان‌دار، جایگاه سفارش خود در صف را ثابت نمی‌کند؛ لاگ پرشدن سفارش کاغذی/کارگزار لازم است. نمونه مصنوعی بالا برای سودآوری استفاده نشده است.

## خروجی و محدودیت

reports شامل شناخت بازار، فرضیه‌ها، معماری، تصمیم اعتبارسنجی و منابع است. results شامل ویژگی‌ها، تحلیل فعالیت سالانه/ماهانه، معاملات، سفارش‌ها، دفتر سرمایه، لاگ یادگیری، حذف اجزا، حساسیت و شاخص‌های کنترل است. بازده/افت در CSV اعشاری است؛ مبالغ خام با فرض ریال‌اند. لاگ‌ها می‌توانند از یک رخداد چند افق هم‌پوشان داشته باشند. ۱۸۷۱ برچسب، ۱۸۷۱ معامله مستقل نیست.

پارامترها برای سودده‌کردن نتیجه آزمون تغییر نکرده‌اند. آینده‌نگری کد بررسی شده، اما تعدیل/بازنویسی تاریخی منبع احراز نشده است. تبدیل تاریخ ماهانه میلادی است و اثر ماه شمسی گزارش نشده. config و rulebook مجوز معامله واقعی ندارند. نسخه بدون زمینه به علت فقط یک معامله مثبت ۲۰۲۶، راهبرد برنده معرفی نشده است.
