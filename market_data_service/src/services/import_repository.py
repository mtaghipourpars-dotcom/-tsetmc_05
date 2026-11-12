"""Import the user's checked-in Markdown price exports without calling a provider."""
import hashlib
from pathlib import Path
from src.repositories.models import raw_responses,sync_errors
from src.services.mapper import map_rows,ensure_symbol
from src.services.normalization import symbol

FILES={'Ayar.md':'عیار','Alton.md':'آلتون','CharismaAhromi.ETF.md':'اهرم',
       'Etemad.Parsian.ETF.md':'اعتماد','Kahroba.md':'کهربا','Moj.ETF-LR .md':'موج',
       'Shetab.ETF.md':'شتاب','Tavan.ETF-LR.md':'توان'}
REQUIRED={'<DTYYYYMMDD>','<FIRST>','<HIGH>','<LOW>','<CLOSE>','<VALUE>','<VOL>','<OPENINT>','<OPEN>','<LAST>'}


def import_history(engine,directory):
    report=[]
    references={}
    snapshots=sorted(Path(directory).glob('MarketWatchPlus-*.md'))
    if snapshots:
        for line in snapshots[-1].read_text().splitlines():
            cells=[c.strip() for c in line.strip('|').split('|')]
            if line.startswith('|') and len(cells)>=15 and cells[0] and cells[1] and cells[0] not in ('نماد','---'):
                references[symbol(cells[0])]=cells[1]
    for filename,name in FILES.items():
        path=Path(directory)/filename
        if not path.is_file():continue
        content=path.read_text()
        lines=[line for line in content.splitlines() if line.startswith('|')]
        header=[s.strip() for s in lines[0].strip('|').split('|')]
        if not REQUIRED <= set(header):raise ValueError('Unexpected source columns: '+filename)
        rows=[]
        for line in lines[2:]:
            values=[s.strip() for s in line.strip('|').split('|')]
            if len(values)!=len(header):raise ValueError('Invalid column count: '+filename)
            r=dict(zip(header,values))
            rows.append({'date':r['<DTYYYYMMDD>'],'pf':r['<FIRST>'],'pmax':r['<HIGH>'],'pmin':r['<LOW>'],
                'pc':r['<CLOSE>'],'pl':r['<LAST>'],'py':r['<OPEN>'],'tno':r['<OPENINT>'],
                'tvol':r['<VOL>'],'tval':r['<VALUE>'],'_data_class':'HISTORICAL','_adjustment_method':'unknown'})
        accepted=rejected=0
        with engine.begin() as conn:
            if name in references:
                ensure_symbol(conn,name,{'l18':name,'l30':references[name],'_reference_source':snapshots[-1].name})
            raw_id=conn.execute(raw_responses.insert().values(source='repository',endpoint='repository_import',
                params={'file':'Data/'+filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'data_class':'HISTORICAL','adjustment_method':'unknown'},payload=rows).returning(raw_responses.c.id)).scalar_one()
            for r in rows:
                try:
                    with conn.begin_nested():
                        map_rows(conn,'history',r,{'l18':name,'type':0},raw_id,source='repository')
                        accepted+=1
                except (ValueError,TypeError):
                    rejected+=1
                    conn.execute(sync_errors.insert().values(raw_id=raw_id,endpoint='repository_import',error_kind='invalid_repository_record',raw=r))
        report.append({'file':filename,'symbol':name,'source':'repository','data_class':'HISTORICAL','accepted':accepted,'rejected':rejected})
    return report
