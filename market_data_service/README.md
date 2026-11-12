## اجرای محلی بدون Docker

برای اجرای مستقیم با Python و SQLite، فایل `START_WINDOWS.bat` در ریشه پروژه را اجرا کنید. [راهنمای گام‌به‌گام](../INSTALL_NO_DOCKER_FA.md). نصب PostgreSQL لازم نیست. فایل `market_data_service/start-docker.bat` مسیر اختیاری Docker است.

# دیدبان — وب‌اپ و پایگاه داده بازار ایران، نسخه ۳

TSETMC/TSE منبع اصلی است. پوشش ۱۶ دسته BrsApi نسخه قبل و امکان fallback حفظ شده است. این سرویس در کنار پروژه پژوهشی قرار دارد و موتورهای معاملاتی مخزن را تغییر نمی‌دهد.

PostgreSQL 16.2، FastAPI و Scheduler واقعاً اجرا شدند. ۱۰٬۲۲۷ رکورد هشت فایل تاریخی مخزن وارد بانک و از HTTP بازیابی شد؛ این داده‌ها با source=repository و برچسب HISTORICAL ثبت شده‌اند. دریافت زنده upstream در این محیط موفق نشده است؛ [گزارش اجرا](docs/LIVE_VALIDATION_FA.md) و [شواهد ماشینی](docs/runtime_verification.json) را ببینید. اجرای محیط موقت، استقرار دائمی برای رایانه شما نیست.

## پنل وب

پس از اجرا، صفحه اصلی در http://localhost:8000 پنل فارسی است. صفحات نمادها، مرکز همگام‌سازی، کاوش داده‌ها و منابع، به بانک واقعی متصل‌اند. مستندات API همچنان در /docs هستند.

برای Windows، در پوشه market_data_service فایل start.bat را اجرا کنید. Python 3.12 برای ساخت تنظیمات اولیه و Docker Desktop برای سرویس‌ها لازم‌اند. setup_env.py کلید مدیریت تصادفی می‌سازد و تنظیمات قبلی را حفظ می‌کند. کلید مدیریت ADMIN_TOKEN در فایل .env شخصی برای شروع/مکث/ادامه دریافت در پنل استفاده می‌شود؛ این کلید با BRS_API_KEY متفاوت است.

در اولین راه‌اندازی، فایل‌های واقعی Data وارد و یک کار دریافت همه نمادها در صف ذخیره می‌شود. collector از صف بانک می‌خواند؛ قطع مرورگر کار را حذف نمی‌کند. [راهنمای وب‌اپ و محدوده جمع‌آوری](docs/WEB_APP_GUIDE_FA.md).

## اجرای محلی

Docker Desktop را اجرا کنید. در این پوشه `.env.example` را به `.env` کپی و ADMIN_TOKEN را به مقدار تصادفی تغییر دهید:

```bash
docker compose up -d --build
```

در Windows از `start.bat` و در Linux/macOS از `./start.sh` نیز می‌توانید استفاده کنید. این دو ابتدا تنظیمات محلی را با Python آماده می‌کنند. [Swagger](http://localhost:8000/docs)، [سلامت](http://localhost:8000/health) و [کاتالوگ](http://localhost:8000/api/tsetmc/catalog) باز می‌شوند. `docker compose down` داده volume را حفظ می‌کند.

کد عمومی حاوی کلید خصوصی نیست. کلید BrsApi فقط در `.env` شخصی تنظیم شود؛ TSETMC به این کلید نیاز ندارد. فایل env از Git و image کنار گذاشته شده است.

## دریافت مستقیم

```bash
docker compose exec api python -m src.cli tsetmc market_watch
docker compose exec api python -m src.cli tsetmc client_all
docker compose exec api python -m src.cli tsetmc indices
docker compose exec api python -m src.cli tsetmc instrument_search --path-params '{"Query":"فملی"}'
docker compose exec api python -m src.cli tsetmc price_history --path-params '{"InsCode":"35425587644337450"}'
```

نقل‌قول این فرمان‌ها برای bash است؛ در Windows می‌توانید از Swagger استفاده کنید. آدرس `POST /api/admin/tsetmc/sync` با هدر `X-Admin-Token` و بدنه:

```json
{"endpoint":"price_history","path_params":{"InsCode":"35425587644337450"},"query":{}}
```

کاتالوگ ۱۳۶ مسیر خواندن داده در ۱۹ خانواده دارد. همه مسیرهای آن به‌صورت on-demand قابل فراخوانی‌اند؛ نماد و تاریخ به چند مقدار ثابت محدود نشده‌اند. Top=0 در مسیر price_history برای همه سوابق استفاده می‌شود؛ معنای آن به سرویس‌های دیگر تعمیم داده نمی‌شود. وجود مسیر در registry به معنی تأیید زنده آن نیست. [فهرست و پارامترها](docs/TSETMC_CATALOG_FA.md).

## زمان‌بندی و اتصال

DATA_PROVIDER=tsetmc پیش‌فرض است. برنامه تهران: bulk دیده‌بان/حقیقی‌حقوقی/شاخص هر دو دقیقه ساعت ۸ تا ۱۸:۵۸؛ اطلاعات، تاریخچه و تعدیل نمادهای منتخب روزانه ۱۸:۰۵؛ جمعه ۱۸:۳۰ مجموعه‌های عمومی. با DATA_PROVIDER=brsapi برنامه نسخه اول برای همه دسته‌های BrsApi اجرا می‌شود.

```bash
docker compose exec api python -m src.cli phase bootstrap
docker compose exec api python -m src.cli phase daily
```

SELECTED_SYMBOLS خالی یعنی همه نمادهای فعال ذخیره‌شده؛ سه نماد پیش‌فرض فقط شروع کار است. قفل PostgreSQL از هم‌پوشانی جلوگیری می‌کند. 429 و Retry-After رعایت می‌شوند؛ در 429 سهمیه با تعویض mirror دور زده نمی‌شود. قطعی شبکه، circuit breaker یک‌دقیقه‌ای دارد.

| تنظیم | کاربرد |
|---|---|
| DATA_PROVIDER | tsetmc یا brsapi |
| TSETMC_BASE_URLS | پیش‌فرض دو میزبان رسمی cdn و cdn10؛ فقط HTTPS رسمی پذیرفته می‌شود |
| TSETMC_PROXY_URL | پراکسی مجاز خودتان؛ بدون ثبت credential در Git یا گزارش |
| BRS_FALLBACK_ENABLED | پیش‌فرض false؛ پس از فعال بودن حساب BrsApi روشن شود |
| BRS_API_KEY | فقط به BrsApi ارسال می‌شود، هرگز به TSETMC |
| ADMIN_TOKEN | هدر X-Admin-Token برای عملیات مدیریتی |
| READ_TOKEN | اختیاری؛ در صورت تنظیم، خواندن داده به X-Api-Token نیاز دارد |
| REQUEST_INTERVAL / REQUEST_TIMEOUT | فاصله و مهلت درخواست مطابق ظرفیت منبع |
| MAX_RETRIES / MAX_RETRY_WAIT | retry قطعی موقت با backoff |

کلاینت از mirrorهای رسمی پشتیبانی می‌کند. استفاده از پراکسی نیازمند مسیر شبکه متعلق به خودتان یا دارای مجوز است؛ فهرست پراکسی ناشناس در پروژه وجود ندارد.

## خواندن داده

| مسیر | خروجی |
|---|---|
| GET /api/symbols | نمادها و ins_code |
| GET /api/symbols/{l18}/history?type=price | قیمت؛ type=client برای حقیقی/حقوقی |
| GET /api/symbols/{l18}/candlesticks?type=adjusted | کندل؛ انواع unadjusted و intraday نیز موجود |
| GET /api/indices?type=1 | شاخص |
| GET /api/data/{dataset} | جداول ساختاریافته ۱۶گانه |
| GET /api/tsetmc/catalog | قراردادهای شناسایی‌شده |
| GET /api/tsetmc/requests | فراداده دریافت‌ها بدون payload حجیم |
| GET /api/tsetmc/requests/{id} | پاسخ کامل، وضعیت، hash و منبع |
| GET /api/tsetmc/observations | رکوردهای مستقیم با فیلتر endpoint/instrument_code |
| GET /api/codal/announcements | اطلاعیه‌های BrsApi ذخیره‌شده |
| POST /api/admin/sync | دریافت یکی از ۱۶ دسته BrsApi |
| GET /api/admin/status | اجراهای BrsApi و خطاهای قرنطینه |

GET فقط بانک را می‌خواند. limit/offset و سقف هر صفحه ۱۰۰۰ است؛ پیمایش صفحات به کل داده دسترسی می‌دهد. مبالغ رشته Decimal هستند. source هر ردیف مشخص است و منابع مستقل همدیگر را بازنویسی نمی‌کنند. صفر، مقدار معتبر است؛ NaN و شمارنده کسری رد می‌شوند. تاریخ provider از زمان دریافت جدا است.

پاسخ تمام خانواده‌های TSETMC در provider_requests و market_observations ثبت می‌شود. نگاشت ساختاریافته برای قیمت تاریخی، snapshot، شاخص، حقیقی/حقوقی تاریخی و معاملات تاریخی وجود دارد؛ خانواده‌های دیگر در آرشیو/observations قابل بازیابی‌اند و مصرف تخصصی آن‌ها نگاشت جدا می‌خواهد. دفتر سفارش خام، دفتر کامل بازسازی‌شده معرفی نمی‌شود. زمان مفقود یا داده کهنه با quality flag مشخص است.

## ورود داده تاریخی همین مخزن

بدون اینترنت و کلید:

```bash
python -m src.cli import-repository ../Data
```

در Docker:

```bash
docker compose cp ../Data api:/tmp/research-data
docker compose exec api python -m src.cli import-repository /tmp/research-data
```

هشت فایل تاریخچه مشخص وارد می‌شوند. کلید روز/نماد/source مانع تکرار است. نوع تعدیل unknown ثبت می‌شود. در قالب فعلی `<FIRST>` قیمت اول، `<OPEN>` قیمت دیروز و `<OPENINT>` تعداد معاملات است. snapshotهای MarketWatch در این واردکننده به OHLC تبدیل نمی‌شوند.

## آزمون و نصب بدون Docker

```bash
pip install -r requirements-dev.txt
pytest -q
```

TEST_POSTGRES_URL باید بانک تست اختصاصی باشد؛ آزمون PostgreSQL schema ایزوله می‌سازد و rollback می‌کند. [خروجی آزمون واقعی](docs/test_output_postgresql.txt). workflow در ریشه مخزن نیز آماده است؛ اجرای موفق آن جدا از آزمون محلی گزارش می‌شود.

برای نصب بدون Docker، Python 3.12 و PostgreSQL 14+ لازم است؛ DATABASE_URL تنظیم شود:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn src.web.app:app --host 127.0.0.1 --port 8000
# ترمینال دوم در Linux/macOS:
python -m src.scheduler.worker
```

import برنامه دریافت شبکه شروع نمی‌کند. زمان‌بند Windows با Docker اجرا شود. snapshotهای migration ثابت‌اند؛ برای تغییر schema، migration جدید بسازید. آرشیو خام retention خودکار ندارد.

## مستندات

- [راهنمای وب‌اپ](docs/WEB_APP_GUIDE_FA.md)
- [گزارش اجرای نسخه ۳](docs/WEB_APP_VALIDATION_FA.md)
- [گزارش اجرای نسخه ۲](docs/LIVE_VALIDATION_FA.md)
- [کاتالوگ TSETMC/TSE](docs/TSETMC_CATALOG_FA.md)
- [قرارداد BrsApi](docs/API_CONTRACT_FA.md)
- [OpenAPI](docs/openapi.json)
- [schema PostgreSQL](docs/schema_postgresql.sql)
- [نتیجه واردکردن داده](docs/repository_import_result.json)
- [مجوز و مراجع inventory](docs/THIRD_PARTY_NOTICES.txt)
