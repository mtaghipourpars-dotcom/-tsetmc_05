# سامانه پژوهش نوسان‌گیری ایران - نسخه تطبیقی

آخرین بررسی: ۱۲ نوامبر ۲۰۲۶. فاز اول: ۱ تا ۱۰ جلسه، یک موقعیت با کل سرمایه قابل تخصیص یا نقد؛ بدون ارسال سفارش واقعی.

## نسخه جاری

پوشه `research_step2/` شناخت ساختار بازار ایران، رفتار جمعی، ممیزی تازگی فرضیه‌ها، مدل یادگیرنده، بک‌تست، حذف اجزا و گزارش نهایی را شامل می‌شود. ضرایب و افق قابل تغییرند، اما کارایی اقتصادی نسخه فعلی تأیید نشد. نسخه کامل در آزمون زمانی بازاستفاده‌شده ۲۰۲۶ حدود ۲۰٫۷۴٪ زیان داشت؛ نسخه بدون زمینه فقط یک معامله مثبت دارد و برنده معرفی نشده است.

- [شناخت بازار و مشارکت‌کنندگان](research_step2/reports/01_MARKET_AND_PARTICIPANTS_FA.md)
- [بازی و فرضیه‌های اختصاصی](research_step2/reports/02_GAME_AND_HYPOTHESES_FA.md)
- [معماری و یادگیری اجراشده](research_step2/reports/03_ADAPTIVE_SYSTEM_FA.md)
- [نتیجه و محدودیت اعتبارسنجی](research_step2/reports/04_VALIDATION_NARRATIVE_FA.md)
- [منابع و ممیزی تازگی](research_step2/reports/05_SOURCES_AND_NOVELTY_FA.md)
- [راهنمای اجرای کامل](research_step2/README_FA.md)

داده‌های اصلی واقعی در `Data/` هستند. آرشیو پژوهشی خارجی سه فایل سهام جداگانه تحلیل شد؛ داده خام خارجی به علت احرازنشدن مجوز بازتوزیع همراه نشده است. fingerprint و دستور دریافت در `research_step2/external_sources.json` و راهنما موجودند. تغییر سهم فعالیت، انتقال همان افراد یا خالص جریان پول نیست.

## اجرای محلی

```bash
python -m pip install -r research_step2/requirements.txt
python research_step2/src/run.py --data Data
python research_step2/src/matched_stress.py --data Data
python -m unittest discover -s research_step2/tests -v
python -m http.server 8000
```

داشبورد تاریخی: `http://localhost:8000/research_step2/results/dashboard.html`

گزارش یکپارچه: `http://localhost:8000/research_step2/results/final_report.html`

۱۳ آزمون موتور در دو مرحله پاس شده‌اند؛ این موضوع صحت داده تعدیل‌شده یا سودآوری را تأیید نمی‌کند. داده رسمی صف، نسخه کامل قوانین، تعدیل و کارمزد تاریخی هنوز ناقص‌اند؛ پیشنهاد خرید واقعی مسدود است. گام اول در `research_step1/` حفظ شده و بازسازی کد موتور قدیمی نیست. اسناد تاریخ‌دار قدیمی، سابقه پروژه‌اند؛ سیاست جاری در [منشور](docs/PROJECT_CHARTER.md) است.
