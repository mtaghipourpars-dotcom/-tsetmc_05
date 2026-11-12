"""Optional Linux PDF renderer using installed Cairo/Pango for native Persian shaping."""
import ctypes as C,ctypes.util,json,re,sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
P=1024

def bind(lib,name,restype,args):
    f=getattr(lib,name);f.restype=restype;f.argtypes=args;return f

class PDF:
    def __init__(self,path):
        ca=C.CDLL(ctypes.util.find_library('cairo'));pa=C.CDLL(ctypes.util.find_library('pango-1.0'));pc=C.CDLL(ctypes.util.find_library('pangocairo-1.0'));go=C.CDLL(ctypes.util.find_library('gobject-2.0'))
        ptr=C.c_void_p;D=C.c_double;I=C.c_int;S=C.c_char_p
        self.surface=bind(ca,'cairo_pdf_surface_create',ptr,[S,D,D])(str(path).encode(),595.276,841.89)
        self.cr=bind(ca,'cairo_create',ptr,[ptr])(self.surface)
        self.rgb=bind(ca,'cairo_set_source_rgb',None,[ptr,D,D,D]);self.rect=bind(ca,'cairo_rectangle',None,[ptr,D,D,D,D]);self.fill=bind(ca,'cairo_fill',None,[ptr]);self.move=bind(ca,'cairo_move_to',None,[ptr,D,D]);self.show=bind(ca,'cairo_show_page',None,[ptr]);self.finish=bind(ca,'cairo_surface_finish',None,[ptr]);self.destroy=bind(ca,'cairo_destroy',None,[ptr]);self.sdestroy=bind(ca,'cairo_surface_destroy',None,[ptr]);self.save=bind(ca,'cairo_save',None,[ptr]);self.restore=bind(ca,'cairo_restore',None,[ptr]);self.translate=bind(ca,'cairo_translate',None,[ptr,D,D]);self.scale=bind(ca,'cairo_scale',None,[ptr,D,D]);self.paint=bind(ca,'cairo_paint',None,[ptr]);self.setsurf=bind(ca,'cairo_set_source_surface',None,[ptr,ptr,D,D]);self.png=bind(ca,'cairo_image_surface_create_from_png',ptr,[S]);self.iw=bind(ca,'cairo_image_surface_get_width',I,[ptr]);self.ih=bind(ca,'cairo_image_surface_get_height',I,[ptr])
        self.layout=bind(pc,'pango_cairo_create_layout',ptr,[ptr]);self.draw=bind(pc,'pango_cairo_show_layout',None,[ptr,ptr]);self.text=bind(pa,'pango_layout_set_text',None,[ptr,S,I]);self.width=bind(pa,'pango_layout_set_width',None,[ptr,I]);self.wrap=bind(pa,'pango_layout_set_wrap',None,[ptr,I]);self.align=bind(pa,'pango_layout_set_alignment',None,[ptr,I]);self.spacing=bind(pa,'pango_layout_set_spacing',None,[ptr,I]);self.size=bind(pa,'pango_layout_get_size',None,[ptr,C.POINTER(I),C.POINTER(I)]);self.font=bind(pa,'pango_layout_set_font_description',None,[ptr,ptr]);self.fdesc=bind(pa,'pango_font_description_from_string',ptr,[S]);self.ffree=bind(pa,'pango_font_description_free',None,[ptr]);self.unref=bind(go,'g_object_unref',None,[ptr]);self.context=bind(pa,'pango_layout_get_context',ptr,[ptr]);self.res=bind(pc,'pango_cairo_context_set_resolution',None,[ptr,D]);self.dir=bind(pa,'pango_context_set_base_dir',None,[ptr,I])
        self.page=0;self.y=0;self.new_page()
    def block(self,text,x,y,w,size=10.5,bold=False,color=(.10,.18,.24),draw=True):
        l=self.layout(self.cr);self.res(self.context(l),72.);self.dir(self.context(l),1)
        font=self.fdesc(('Noto Sans Arabic '+('Bold ' if bold else '')+str(size)).encode());self.font(l,font);self.ffree(font)
        self.width(l,int(w*P));self.wrap(l,2);self.align(l,2);self.spacing(l,int(2.7*P));raw=text.encode();self.text(l,raw,len(raw))
        xx=C.c_int();yy=C.c_int();self.size(l,C.byref(xx),C.byref(yy));h=yy.value/P
        if draw:self.rgb(self.cr,*color);self.move(self.cr,x,y);self.draw(self.cr,l)
        self.unref(l);return h
    def new_page(self):
        if self.page:self.footer();self.show(self.cr)
        self.page+=1;self.y=52
        self.rgb(self.cr,.10,.24,.32);self.rect(self.cr,44,32,507,2);self.fill(self.cr)
        self.block('پژوهش بازار ایران | نسخه نهایی ۱۲ نوامبر ۲۰۲۶',44,14,507,7.7,color=(.35,.43,.47))
    def footer(self):
        self.block('صفحه '+str(self.page)+' | پژوهش تاریخی؛ بدون مجوز معامله واقعی',44,805,507,7.5,color=(.35,.43,.47))
    def ensure(self,h):
        if self.y+h>786:self.new_page()
    def paragraph(self,text,size=10.3,bold=False):
        text=re.sub(r'`([^`]+)`',r'\1',text);text=text.replace('**','')
        h=self.block(text,44,0,507,size,bold,draw=False)
        if h>700:
            words=text.split();part=[]
            for word in words:
                part.append(word)
                if self.block(' '.join(part),44,0,507,size,bold,draw=False)>300:
                    self.paragraph(' '.join(part[:-1]),size,bold);part=[word]
            if part:self.paragraph(' '.join(part),size,bold)
            return
        self.ensure(h+10);self.block(text,44,self.y,507,size,bold);self.y+=h+9
    def heading(self,text,level):
        self.ensure(85 if level==1 else 65);self.y+=10
        h=self.block(text,44,self.y,507,18 if level==1 else 13.2,True,color=(.07,.30,.40));self.y+=h+10
    def table(self,rows,keep=False):
        if not rows:return
        n=len(rows[0]);width=507/n;size=8.7 if n<=4 else 7.8;header=rows[0]
        def heights(row):return max(self.block(str(v),0,0,width-10,size,draw=False) for v in row)+12
        total=sum(heights(row) for row in rows)
        self.ensure((total if keep and total<650 else sum(heights(r) for r in rows[:2]))+12)
        def draw(row,j):
            h=heights(row)
            for k,v in enumerate(row):
                x=44+507-(k+1)*width
                bg=(.10,.25,.33) if j==0 else ((.94,.96,.97) if j%2==0 else (.99,.99,.99))
                self.rgb(self.cr,*bg);self.rect(self.cr,x,self.y,width-.7,h-.7);self.fill(self.cr)
                self.block(str(v),x+5,self.y+5,width-10,size,j==0,color=(1,1,1) if j==0 else (.10,.18,.24))
            self.y+=h
        for j,row in enumerate(rows):
            h=heights(row)
            if self.y+h>784:
                self.new_page()
                if j>0:draw(header,0)
            draw(row,j)
        self.y+=12
    def image(self,path):
        surf=self.png(str(path).encode());w=self.iw(surf);h=self.ih(surf);s=507/w;hh=h*s
        self.ensure(hh+10);self.save(self.cr);self.translate(self.cr,44,self.y);self.scale(self.cr,s,s);self.setsurf(self.cr,surf,0,0);self.paint(self.cr);self.restore(self.cr);self.sdestroy(surf);self.y+=hh+10
    def markdown(self,text):
        lines=text.splitlines();i=0;para=[]
        def flush():
            if para:self.paragraph(' '.join(para));para.clear()
        while i<len(lines):
            s=lines[i]
            if s.startswith('|'):
                flush();rows=[]
                while i<len(lines) and lines[i].startswith('|'):
                    vals=[v.strip() for v in lines[i].split('|')[1:-1]]
                    if not all(re.fullmatch(r'[-: ]+',v or '-') for v in vals):rows.append(vals)
                    i+=1
                self.table(rows);continue
            elif s.startswith('#'):
                flush();n=len(s)-len(s.lstrip('#'))
                next_lines=[v for v in lines[i+1:] if v.strip()]
                if next_lines and next_lines[0].startswith('|'):
                    first=[]
                    for v in next_lines:
                        if not v.startswith('|'):break
                        vals=[w.strip() for w in v.split('|')[1:-1]]
                        if not all(re.fullmatch(r'[-: ]+',w or '-') for w in vals):first.append(vals)
                        if len(first)==2:break
                    if first:
                        width=507/len(first[0]);sz=8.7 if len(first[0])<=4 else 7.8
                        hh=sum(max(self.block(v,0,0,width-10,sz,draw=False) for v in row)+12 for row in first)
                        self.ensure(hh+70)
                self.heading(s[n:].strip(),n)
            elif not s.strip():flush()
            else:para.append(s)
            i+=1
        flush()
    def close(self):self.footer();self.show(self.cr);self.finish(self.surface);self.destroy(self.cr);self.sdestroy(self.surface)

def pct(x):return 'ناموجود' if pd.isna(x) else f'{x*100:+.2f}%'

def main(path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=ROOT/'results';tmp=ROOT.parent/'tmp'/'pdfs';tmp.mkdir(parents=True,exist_ok=True)
    # Render the scientific plots at 240 dpi without reshaping any data.
    share=pd.read_csv(out/'group_activity_share.csv',index_col=0,parse_dates=True).resample('ME').mean()
    fig,ax=plt.subplots(figsize=(9,3.4));ax.stackplot(share.index,share.gold,share.equity,share.income,labels=['Gold (3)','Leveraged equity (4)','Income (1)'],colors=['#d2a637','#327f9e','#8f9f9b']);ax.set_ylim(0,1);ax.legend(fontsize=8);ax.set_ylabel('Share of trading value within selected 8');fig.tight_layout();fig.savefig(tmp/'activity.png',dpi=240);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,3.4))
    for name in ['adaptive','repair','relay','supply_relief','simple','momentum']:
        d=pd.read_csv(out/f'{name}_equity.csv');ax.plot(pd.to_datetime(d.date),d.equity/d.equity.iloc[0],label=name,linewidth=1.2)
    ax.legend(ncol=3,fontsize=8);ax.grid(alpha=.2);ax.set_ylabel('Research marked equity / initial');fig.tight_layout();fig.savefig(tmp/'equity.png',dpi=240);plt.close(fig)
    pdf=PDF(path);pdf.y=90;pdf.paragraph('گزارش نهایی پژوهش و طراحی',14,True);pdf.heading('بازی قابل اجرا در بازار ایران',1);pdf.paragraph('از شناخت رفتار جمعی تا یادگیری و سنجش حق خروج',16,True);pdf.paragraph('افق ۱ تا ۱۰ جلسه | یک موقعیت با کل سرمایه یا نقد',12)
    pdf.y+=20;pdf.paragraph('نتیجه اصلی: سامانه تطبیقی پژوهشی ساخته و آزموده شد؛ نسخه فعلی برای استفاده عملیاتی پذیرفته نشد. داده رسمی اجرای صف و تعدیل تاریخی هنوز کافی نیست.',13,True)
    pdf.table([['نامزد پژوهش','تازگی/تمایز','وضعیت'],['جذب پایدار و نسخه مقررات','ظرفیت خروج کل سرمایه، نه صرف جمع‌شدن صف','داده زمان‌دار لازم است'],['عمر تقاضای موقت مقصد','فراتر از چرخش ساده و روز هفته','تقویم/جریان لازم است'],['رقابت تقاضای تازه و عرضه رهایی','فراتر از لنگر قیمتی خام','کوهورت/مظنه لازم است'],['سه جانشین و یادگیرنده','نمونه اجرا و ابطال اجزا','رد ارتقای عملیاتی']])
    pdf.paragraph('محتوا: شناخت بازار و مشارکت‌کنندگان؛ بازی و فرضیه‌ها؛ معماری تطبیقی؛ نتایج محاسبه‌شده؛ منابع و ممیزی تازگی.');pdf.paragraph('۱۲ نوامبر ۲۰۲۶ | داده صندوق‌ها تا ۱۱ نوامبر؛ آرشیو سهام مستقل تا ژوئن ۲۰۲۱',10)
    for filename in ['01_MARKET_AND_PARTICIPANTS_FA.md','02_GAME_AND_HYPOTHESES_FA.md','03_ADAPTIVE_SYSTEM_FA.md','04_VALIDATION_NARRATIVE_FA.md']:
        pdf.new_page();pdf.markdown((ROOT/'reports'/filename).read_text())
    pdf.new_page();pdf.heading('جدول‌ها و نمودارهای محاسبه‌شده',1)
    y=pd.read_csv(out/'behavior_yearly.csv');pdf.heading('سهم فعالیت در سبد ثابت هشت صندوق',2)
    pdf.table([['سال میلادی','مشاهده','طلا','اهرمـی','درآمد ثابت','همبستگی','هر دو منفی']]+[[str(r.year),str(int(r.n)),pct(r.gold_share),pct(r.equity_share),pct(r.income_share),f'{r.gold_equity_corr:.3f}',pct(r.joint_down_fraction)] for r in y.itertuples()]);pdf.image(tmp/'activity.png');pdf.paragraph('سهم از ارزش معاملات همین هشت صندوق، نه کل بازار یا خالص ورود پول. سال‌های ۲۰۲۳ و ۲۰۲۶ کامل نیستند.',9)
    ex=pd.read_csv(out/'external_activity_yearly.csv');ex=ex[ex.year.isin([2015,2016,2017,2018,2019,2020,2021])].pivot(index='year',columns='symbol',values='activity_share')
    pdf.heading('ترکیب فعالیت آرشیو سه فایل سهام',2);pdf.table([['سال میلادی','فایل منتسب به مس','فایل منتسب به فولاد','فایل منتسب به خودرو']]+[[str(yr),pct(r.fameli_candidate),pct(r.foolad_candidate),pct(r.khodro_candidate)] for yr,r in ex.iterrows()]);pdf.paragraph('نامزد نگاشت از نام فایل؛ شناسه رسمی مستقل احراز نشده. تغییر فعالیت، هویت یا انگیزه همان اشخاص را ثابت نمی‌کند.',9)
    pdf.heading('عملکرد شبیه‌سازی پایه',1);m=pd.read_csv(out/'strategy_metrics.csv');base=m[(m.capital_rial==1e9)&(m.scenario=='base')&(m.period!='ALL')]
    names={'repair':'ترمیم فعالیت','relay':'انتقال فعالیت','supply_relief':'کاهش جرم بالاسر','simple':'بازگشت ساده','momentum':'مومنتوم معیار','adaptive':'یادگیرنده کامل','adaptive_no_context':'بدون زمینه','adaptive_no_forgetting':'بدون فراموشی'}
    for yr,sub in base.groupby('period'):
        pdf.table([['سال','نسخه','بازده خالص','افت بیشینه','خروج کامل','مواجهه']]+[[str(r.period),names[r.mode],pct(r.net_return),pct(r.max_drawdown),str(int(r.trades)),pct(r.exposure)] for r in sub.itertuples()],keep=True)
    pdf.image(tmp/'equity.png');pdf.paragraph('سرمایه اولیه مفروض ۱۰۰ میلیون تومان؛ دوره‌ها بازاستفاده‌شده‌اند. بازده سالانه ارزش‌گذاری می‌شود؛ تعداد معامله بر اساس سال خروج است.',9)
    pdf.heading('حساسیت یادگیرنده کامل در ۲۰۲۶',2);s=m[(m['mode']=='adaptive')&(m.period=='2026')]
    pdf.table([['سرمایه تومان، مشروط','سناریو','بازده','افت','معامله']]+[[f'{r.capital_rial/10:,.0f}',r.scenario,pct(r.net_return),pct(r.max_drawdown),str(int(r.trades))] for r in s.itertuples()])
    ci=pd.read_csv(out/'block_bootstrap_2026.csv');pdf.heading('فاصله بازنمونه‌گیری میانگین روزانه',2);pdf.table([['نسخه','میانگین روزانه','کران پایین','کران بالا']]+[[names[r.mode],pct(r.mean_daily),pct(r.ci_low),pct(r.ci_high)] for r in ci.itertuples()]);pdf.paragraph('بلوک ده مشاهده، هزار تکرار، بدون اصلاح کامل آزمون‌های متعدد؛ این فاصله احتمال سود آینده نیست.',9)
    pdf.new_page();sources=(ROOT/'reports/05_SOURCES_AND_NOVELTY_FA.md').read_text();pdf.markdown(sources.split('عبارت‌های جست‌وجو شامل')[0]);pdf.close();print('PDF pages',pdf.page,'path',path)

if __name__=='__main__':
    target=Path(sys.argv[1]);target.parent.mkdir(parents=True,exist_ok=True);main(target)
