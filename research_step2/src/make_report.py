from pathlib import Path
import json,re,html,sys
import numpy as np
import pandas as pd
from engine import ROOT,NAMES,load,build_features,Learner,safety,FAMILIES,make_labels
from governance import live_gate

OUT=ROOT/'results'

def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'(https?://[^\s<]+)',r'<a dir="ltr" href="\1">\1</a>',s)
    return s

def md(text):
    lines=text.splitlines();out=[];i=0;para=[]
    def flush():
        if para:out.append('<p>'+inline(' '.join(para))+'</p>');para.clear()
    while i<len(lines):
        s=lines[i]
        if s.startswith('```'):
            flush();code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
            out.append('<pre dir="ltr">'+html.escape('\n'.join(code))+'</pre>')
        elif s.startswith('|'):
            flush();rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                vals=[v.strip() for v in lines[i].split('|')[1:-1]]
                if not all(re.fullmatch(r'[-: ]+',v or '-') for v in vals):rows.append(vals)
                i+=1
            out.append('<table>'+''.join('<tr>'+''.join(('<th>' if j==0 else '<td>')+inline(v)+('</th>' if j==0 else '</td>') for v in row)+'</tr>' for j,row in enumerate(rows))+'</table>');continue
        elif s.startswith('#'):
            flush();n=len(s)-len(s.lstrip('#'));out.append(f'<h{n}>{inline(s[n:].strip())}</h{n}>')
        elif not s.strip():flush()
        else:para.append(s)
        i+=1
    flush();return '\n'.join(out)

STYLE='''
@font-face{font-family:Persian;src:url("file:///usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf")}
@font-face{font-family:Persian;src:url("file:///usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf");font-weight:700}
*{box-sizing:border-box}body{font-family:Persian,Tahoma,sans-serif;color:#1b2c3c;line-height:1.9;margin:0;background:#edf1f4;font-size:13px}
main{max-width:1080px;margin:auto;background:white;padding:48px}h1{font-size:25px;line-height:1.8;color:#123d56;border-bottom:3px solid #d6ab47;padding-bottom:10px;margin-top:30px}h2{font-size:18px;color:#145473;margin-top:28px}h3{font-size:15px}
p{margin:10px 0;text-align:justify}table{border-collapse:collapse;width:100%;margin:18px 0;font-size:11px;line-height:1.8}th{background:#183e54;color:#fff;font-weight:700}th,td{border:1px solid #d6dfe5;padding:8px;vertical-align:top}tr:nth-child(even)td{background:#f2f6f8}a{color:#116684;text-decoration:none;overflow-wrap:anywhere}code,pre{font-family:monospace;background:#edf2f5;overflow-wrap:anywhere}pre{padding:15px;white-space:pre-wrap;font-size:11px;line-height:1.6;direction:ltr;text-align:left}.eyebrow{color:#906a18;font-size:13px}.cover{padding:35px 0 24px}.cover h1{font-size:34px;border:0}.callout{border-right:5px solid #b78928;background:#fbf7ed;padding:15px 20px;margin:18px 0}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.card{padding:18px;background:#edf3f6;border-radius:10px}.card strong{font-size:24px;display:block}.chart{width:100%;margin:14px 0}.caption{font-size:10px;color:#536976}.section{margin-top:32px}.compact{font-size:10px}.muted{color:#536976}
@page{size:A4;margin:17mm 16mm 19mm} @media print{body{background:white;font-size:10.4px;line-height:1.75}main{padding:0;max-width:none}h1{font-size:20px}h2{font-size:14px}h1,h2,h3{break-after:avoid}p{orphans:3;widows:3}table{font-size:8.4px;line-height:1.65}th,td{padding:5px}thead{display:table-header-group}tr{break-inside:avoid}section{break-before:page}.cover{break-after:page}.chart{max-height:80mm;object-fit:contain}.cards{display:flex}.card{width:33%}.callout{break-inside:avoid}pre{font-size:9px}.section{margin-top:0}}
'''

def percent(v):return 'محاسبه نشده' if pd.isna(v) else f'{100*v:+.2f}٪'
def table(df):return df.to_html(index=False,escape=True,border=0)

def numerical_sections():
    yearly=pd.read_csv(OUT/'behavior_yearly.csv');y=yearly.copy()
    for k in ['gold_share','equity_share','income_share','joint_down_fraction']:y[k]=y[k].map(lambda v:f'{100*v:.1f}٪')
    y['gold_equity_corr']=y.gold_equity_corr.map(lambda v:f'{v:.3f}')
    y=y.rename(columns={'year':'سال میلادی','n':'مشاهده','gold_share':'سهم طلا','equity_share':'سهم اهرمی','income_share':'سهم درآمد ثابت','gold_equity_corr':'همبستگی بازده','joint_down_fraction':'هر دو منفی','dominant_activity_switches':'تعویض گروه غالب'})
    ex=pd.read_csv(OUT/'external_activity_yearly.csv');ex=ex[ex.year.isin([2015,2016,2017,2018,2019,2020,2021])].pivot(index='year',columns='symbol',values='activity_share').reset_index()
    ex=ex.rename(columns={'year':'سال میلادی','fameli_candidate':'فایل منتسب به فملی','foolad_candidate':'فایل منتسب به فولاد','khodro_candidate':'فایل منتسب به خودرو'})
    for col in ex.columns[1:]:ex[col]=ex[col].map(lambda v:f'{100*v:.1f}٪')
    m=pd.read_csv(OUT/'strategy_metrics.csv');base=m[(m.capital_rial==1e9)&(m.scenario=='base')&(m.period!='ALL')].copy()
    names={'repair':'ترمیم فعالیت','relay':'انتقال فعالیت','supply_relief':'کاهش جرم بالاسر','simple':'بازگشت ساده','momentum':'مومنتوم معیار','adaptive':'یادگیرنده کامل','adaptive_no_context':'بدون زمینه','adaptive_no_forgetting':'بدون فراموشی'}
    base['mode']=base['mode'].map(names)
    for col in ['net_return','max_drawdown','exposure']:base[col]=base[col].map(percent)
    base=base[['period','mode','net_return','max_drawdown','trades','exposure']].rename(columns={'period':'سال','mode':'نسخه','net_return':'بازده خالص','max_drawdown':'افت بیشینه','trades':'خروج کامل','exposure':'مواجهه'})
    sensitivity=m[(m['mode']=='adaptive')&(m.period=='2026')][['capital_rial','scenario','net_return','max_drawdown','trades']].copy()
    sensitivity.capital_rial=sensitivity.capital_rial.map(lambda v:f'{v/10:,.0f}')
    for c in ['net_return','max_drawdown']:sensitivity[c]=sensitivity[c].map(percent)
    sensitivity=sensitivity.rename(columns={'capital_rial':'سرمایه تومان، مشروط','scenario':'سناریو','net_return':'بازده','max_drawdown':'افت','trades':'معامله بسته'})
    ci=pd.read_csv(OUT/'block_bootstrap_2026.csv');ci['mode']=ci['mode'].map(names)
    for col in ['mean_daily','ci_low','ci_high']:ci[col]=ci[col].map(percent)
    ci=ci[['mode','mean_daily','ci_low','ci_high']].rename(columns={'mode':'نسخه','mean_daily':'میانگین روزانه','ci_low':'کران پایین','ci_high':'کران بالا'})
    return '<h2>رفتار سالانه: فقط سبد ثابت هشت صندوق</h2>'+table(y)+'<img class="chart" src="activity_share.svg"><p class="caption">سهم متوسط ماهانه از ارزش معاملات هشت ابزار؛ سهم از کل بازار یا خالص جریان پول نیست. ۲۰۲۳ و ۲۰۲۶ سال کامل نیستند.</p><h2>تغییر نقش سه فایل سهام در آرشیو قدیمی</h2>'+table(ex)+'<p>نام نماد از نام فایل استنباط شده؛ شناسه رسمی مستقل احراز نشده است. ۲۰۲۱ ناقص است. این جدول سهم فعالیت جمعی را نشان می‌دهد، نه جابه‌جایی همان افراد.</p><h2>بازده و افت شبیه‌سازی پایه</h2>'+table(base)+'<img class="chart" src="research_equity.svg"><p class="caption">سرمایه علامت‌گذاری‌شده نسبت به آغاز دوره؛ هزینه و اجرای روزانه مفروض. منحنی‌ها تأیید معامله‌پذیری نیستند.</p><h2>حساسیت نسخه کامل در ۲۰۲۶</h2>'+table(sensitivity)+'<p>حالت فشار ممکن است اصلاً وارد معامله نشود. صفر بودن سود/زیان ناشی از نقدماندن، پیش‌بینی درست بازار نیست. سناریوها می‌توانند مجموعه معاملات را عوض کنند.</p><h2>عدم قطعیت میانگین بازده روزانه ۲۰۲۶</h2>'+table(ci)+'<p>بازنمونه‌گیری بلوکی ۱۰ مشاهده، ۱۰۰۰ تکرار؛ اصلاح انتخاب از آزمون‌های متعدد انجام نشده است. این جدول احتمال سود آینده نیست.</p>'

def dashboard():
    m=pd.read_csv(OUT/'strategy_metrics.csv');last=pd.read_csv(OUT/'behavior_features.csv');last=last[last.i==last.i.max()].copy()
    label_df=pd.read_csv(OUT/'matured_shadow_labels.csv');cfg=json.loads((ROOT/'config.json').read_text())
    # Latest independent display uses only matured data, respecting the last long-gap epoch.
    group_dates=pd.read_csv(OUT/'group_returns.csv',index_col=0).index;days=pd.DatetimeIndex(pd.to_datetime(group_dates))
    max_i=int(last.i.max());gaps=np.flatnonzero(days.to_series().diff().dt.days.gt(21).to_numpy());epoch=int(gaps[-1]) if len(gaps) else 0
    # Load the coefficient vectors/features from the archived opportunity data without fabricating labels.
    data_path=ROOT.parent/'repo'/'Data'
    if not data_path.exists():data_path=ROOT.parent/'Data'
    frames,_=load(data_path,OUT);panel,*_=build_features(frames,days,cfg)
    labels,_=make_labels(frames,days,panel,cfg,1e9,cfg['fee'],cfg['slippage'],cfg['participation'])
    model=Learner(cfg);model.add_matured([r for r in labels if r['maturity_i']<=max_i and r['signal_i']>=epoch],max_i)
    alternatives=[]
    for row in last.to_dict('records'):
        safe,reason=safety(row,days,cfg);scores=[]
        for fam in FAMILIES:
            if not row[fam]:continue
            for h in cfg['horizons']:
                s=model.score(dict(row,family=fam),h,max_i)
                if s is not None:scores.append(dict(family=fam,h=h,score=s['score']))
        best=max(scores,key=lambda r:r['score']) if scores else None
        alternatives.append(dict(symbol=row['symbol'],name=NAMES[row['symbol']],safe_proxy=safe,reason=reason,
              research_score=best['score'] if best else None,hold=best['h'] if best else None,
              capacity_toman_assumed=row['capacity']/10,live_recommendation=False,estimated_profit=None))
    alternatives.append(dict(symbol='Etemad.Parsian.ETF',name='اعتماد پارسیان',safe_proxy=False,reason='reference_income_not_cash',research_score=None,hold=None,
        capacity_toman_assumed=float(frames['Etemad.Parsian.ETF'].VALUE.tail(20).min())*.001,live_recommendation=False,estimated_profit=None))
    alternatives.sort(key=lambda r:(r['research_score'] is None,-(r['research_score'] or 0)))
    snapshot=dict(as_of=str(days[-1].date()),real_position=None,realized_profit=None,forecast_profit=None,alternatives=alternatives,live_gate=live_gate(cfg),mode='HISTORICAL_RESEARCH')
    (OUT/'dashboard_snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
    reasons={'reported_rule_change_quarantine':'وقفه پژوهشی پس از تغییر مقررات گزارش‌شده','reference_income_not_cash':'دارایی مرجع درآمد ثابت؛ با وجه نقد یکی نیست','data_gap_corporate_or_single_price':'شکاف داده، رویداد نامعلوم یا تک‌قیمت','joint_market_stress':'فشار همزمان دو گروه','missing_features':'داده ویژگی‌ها ناقص است'}
    rows=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [r['name'],'فاقد شواهد کافی' if r['research_score'] is None else f"{r['research_score']:.5f}",r['hold'] or 'نامشخص',f"{r['capacity_toman_assumed']:,.0f}",reasons.get(r['reason'],'کنترل روزانه گذرانده؛ اجرای واقعی احراز نشده')])+'</tr>' for r in alternatives)
    body=f'''<div class="eyebrow">آخرین داده: {snapshot['as_of']} | تاریخی، بدون اتصال کارگزاری</div><h1>تصمیم‌یار نوسان‌گیری تطبیقی</h1><div class="cards"><div class="card">موقعیت واقعی<strong>ثبت نشده</strong>تاریخ خرید و سود واقعی نامعلوم</div><div class="card">وضعیت مدل<strong>رد عملیاتی</strong>یادگیرنده کامل: ۲۰٫۷۴٪ زیان در ۲۰۲۶</div><div class="card">اجازه سفارش<strong>مسدود</strong>داده اجرا و مقررات تأیید نشده</div></div><div class="callout">رتبه‌ها فقط امتیاز پژوهشی‌اند. هیچ سود پیش‌بینی‌شده یا زمان فروش معتبر ساخته نشده است. ظرفیت زیر فرضی و مشروط به ریال بودن منبع است.</div><h2>گزینه‌های منتخب</h2><table><tr><th>دارایی</th><th>امتیاز پژوهشی</th><th>افق نامزد</th><th>ظرفیت مفروض تومان</th><th>دلیل/کیفیت</th></tr>{rows}</table><h2>تغییر ترکیب فعالیت</h2><img class="chart" src="activity_share.svg"><h2>کارنامه پژوهشی</h2><img class="chart" src="research_equity.svg"><p><a href="final_report.html">گزارش کامل شناخت بازار، فرضیه‌ها و ارزیابی</a></p>'''
    (OUT/'dashboard.html').write_text('<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><title>داشبورد پژوهش تطبیقی</title><style>'+STYLE+'</style><main>'+body+'</main></html>')

def main():
    intro='''<div class="cover"><div class="eyebrow">گزارش نهایی پژوهش و طراحی | ۱۲ نوامبر ۲۰۲۶</div><h1>بازی قابل اجرا در بازار ایران<br>از رفتار جمعی تا یادگیری و حق خروج</h1><p>دارایی‌های منتخب؛ افق ۱ تا ۱۰ جلسه؛ یک موقعیت با کل سرمایه یا نقد</p><div class="callout"><strong>نتیجه تصمیم:</strong> مدل تطبیقی ساخته و آزموده شد؛ نسخه فعلی برای معامله عملیاتی پذیرفته نشد. شناخت بازار و طراحی اختصاصی، جای شواهد سودآوری و اجرای سفارش را نمی‌گیرند.</div><h2>مقایسه و اولویت پژوهش</h2><table><tr><th>گزینه</th><th>تازگی قابل دفاع</th><th>شواهد اجرا</th><th>وضعیت</th></tr><tr><td>جذب پایدار با نسخه مقررات و ظرفیت خروج</td><td>طراحی اختصاصی، تقدم جهانی اثبات نشده</td><td>دفتر سفارش لازم است</td><td>اولویت پژوهش، تأییدنشده</td></tr><tr><td>عمر تقاضای موقت میان بازارها</td><td>تفاوت با چرخش خام تعریف شده</td><td>تقویم/جریان زمان‌دار لازم است</td><td>تعلیق تا داده</td></tr><tr><td>رقابت خرید تازه با عرضه در رهایی</td><td>تفاوت با لنگر خام تعریف شده</td><td>کوهورت/مظنه لازم است</td><td>تعلیق تا داده</td></tr><tr><td>سه جانشین روزانه و یادگیرنده</td><td>ابزار مقایسه، کشف بکر نیست</td><td>شبیه‌سازی روزانه اجرا شد</td><td>رد ارتقای عملیاتی</td></tr></table><p>محتوا: ۱. شناخت بازار و مشارکت‌کنندگان؛ ۲. استدلال و فرضیه‌ها؛ ۳. معماری و یادگیری؛ ۴. ارزیابی عددی؛ ۵. منابع و ممیزی تازگی.</p><p class="muted">داده فعلی صندوق‌ها تا ۱۱ نوامبر ۲۰۲۶؛ آرشیو سهام مستقل تا ژوئن ۲۰۲۱. این گزارش پیش‌بینی قطعی، ادعای تجربه شخصی معامله‌گری یا وعده سود ندارد.</p></div>'''
    pieces=[intro]
    for file in ['01_MARKET_AND_PARTICIPANTS_FA.md','02_GAME_AND_HYPOTHESES_FA.md','03_ADAPTIVE_SYSTEM_FA.md','04_VALIDATION_NARRATIVE_FA.md']:
        pieces.append('<section>'+md((ROOT/'reports'/file).read_text())+'</section>')
        if file.startswith('04'):pieces.append('<section><h1>جدول‌ها و نمودارهای محاسبه‌شده</h1>'+numerical_sections()+'</section>')
    pieces.append('<section>'+md((ROOT/'reports/05_SOURCES_AND_NOVELTY_FA.md').read_text())+'</section>')
    (OUT/'final_report.html').write_text('<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>گزارش نهایی سیستم تطبیقی ایران</title><style>'+STYLE+'</style></head><body><main>'+''.join(pieces)+'</main></body></html>')
    dashboard();print('Created final_report.html, dashboard.html, dashboard_snapshot.json')

if __name__=='__main__':main()
