# فهرست اقلام پروژه و وضعیت انتقال

این سند موجودی فایل‌های تولیدشده/دریافت‌شده در محیط کار را ثبت می‌کند. وجود یک فایل در این فهرست به معنی وجود بایت‌های آن در GitHub نیست؛ وضعیت انتقال صریحاً مشخص شده است.

## اقلام متنی/مستندات منبع
- سند جامع سیستم معاملاتی اشباع‌شدگی بورس تهران (PDF) — در محیط کار موجود؛ انتقال باینری به GitHub در این مرحله انجام نشده.
- فهرست جامع SKILLهای موردنیاز (Markdown) — در محیط کار موجود؛ انتقال متن کامل انجام نشده.
- مشخصات فنی Trading Engine v3.0 DRAFT (Markdown) — در محیط کار موجود؛ انتقال متن کامل انجام نشده.
- code_artifact.md و سه متن pasted — در محیط کار موجود؛ نیازمند دسته‌بندی و حذف اطلاعات تکراری/حساس قبل از انتشار.

## داده‌های خام
- Moj.ETF-LR.csv
- Shetab.Farabi.ETF.csv
- CharismaAhromi ETF (5).csv
- Tavan.ETF-LR.csv
- Ayar (5).csv
- Kahroba.csv
- Alton.csv
- Etemad Parsian ETF (5).csv
- MarketWatch.xls (در عمل HTML snapshot)

## خروجی‌های پردازش‌شده
- Saturation_6Asset_Data_Audit_and_Signal_Diagnostic_2026-11-06.md
- Saturation_6Asset_Benchmark_Metrics_2026-11-06.csv
- Saturation_6Asset_Signal_Diagnostic_2026-11-06.csv
- Saturation_Full_8Asset_Replay_Audit_2026-11-06.md
- Saturation_Full_8Asset_Backtest_Metrics_2026-11-06.csv
- Saturation_Full_8Asset_Data_Audit_2026-11-06.csv
- Saturation_Full_8Asset_Equity_Curve_2026-11-06.csv
- Saturation_Full_8Asset_Trades_2026-11-06.csv
- Saturation_RiskLimited_EngineA_v2_Report_2026-11-06.md
- Saturation_RiskLimited_EngineA_v2_Metrics_2026-11-06.csv
- Saturation_RiskLimited_EngineA_v2_Daily_Equity_2026-11-06.csv
- Saturation_RiskLimited_EngineA_v2_Entries_2026-11-06.csv
- Saturation_RiskLimited_EngineA_v2_Events_2026-11-06.csv
- Saturation_RiskLimited_EngineA_v2_Slippage_Sensitivity_2026-11-06.csv
- Saturation_RiskLimited_EngineA_v2_Benchmarks_2026-11-06.csv
- Saturation_RiskLimited_EngineA_v2_Breakeven_Slippage_2026-11-06.csv
- Saturation_RiskLimited_EngineA_v2_Data_Audit_2026-11-06.csv

## کدها و بسته‌ها
- rebuild_backtest_v3_1.py
- run_risk_limited_engine_a_v2.py
- Saturation_8Asset_Backtest_Package_2026-11-06.zip
- Saturation_RiskLimited_EngineA_v2_Package_2026-11-06.zip
- Saturation_RiskLimited_EngineA_v2_Results.xlsx
- Iran_Trading_System_60_Skills_v1.0.0.zip (۶۰ فایل Skill به‌علاوه کاتالوگ و README)

## وضعیت GitHub در این commit
در این مرحله فقط README و اسناد معماری/روش‌شناسی/وضعیت/فهرست انتقال به‌صورت فایل‌های متنی در مخزن ثبت می‌شوند. انتقال بایت‌به‌بایت فایل‌های خام، PDF، ZIP، XLSX، PNG و CSVهای حجیم از طریق ابزار اتصال GitHub موجود در این محیط پشتیبانی مستقیم ندارد؛ بنابراین آن‌ها را «آپلودشده» علامت نمی‌زنیم. برای تکمیل انتقال باینری باید از Git client یا Git LFS/آپلود فایل در محیطی با دسترسی نوشتن مستقیم استفاده شود.

## کنترل تمامیت
برای انتقال بعدی، SHA-256 هر فایل در محیط مبدأ محاسبه و پس از انتقال دوباره محاسبه شود. از جایگزینی داده خام با فایل‌های بازتولیدشده یا تخمینی خودداری شود.
