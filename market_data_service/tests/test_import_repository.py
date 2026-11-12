from pathlib import Path
from sqlalchemy import select
from src.repositories.models import TABLES
from src.services.import_repository import import_history


def test_import_real_file_format_preserves_provenance_and_zero(tmp_path,engine):
    (tmp_path/'Ayar.md').write_text('| <TICKER> | <DTYYYYMMDD> | <FIRST> | <HIGH> | <LOW> | <CLOSE> | <VALUE> | <VOL> | <OPENINT> | <PER> | <OPEN> | <LAST> |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| Ayar | 20261111 | 0.00 | 100.00 | 0.00 | 90.00 | 900 | 10 | 2 | D | 80.00 | 95.00 |\n')
    for _ in range(2):
        report=import_history(engine,tmp_path)
        assert report[0]['accepted']==1 and report[0]['rejected']==0
    with engine.connect() as conn:
        row=conn.execute(select(TABLES['price_history'])).mappings().one()
        assert row['source']=='repository' and row['price_first']==0 and row['price_yesterday']==80
        assert row['raw']['_data_class']=='HISTORICAL' and row['raw']['_adjustment_method']=='unknown'


def test_v1_brs_natural_key_compatible():
    from src.services.mapper import provider_key
    from src.services.normalization import digest
    assert provider_key('brsapi','price_history',1,'1405-01-01')==digest('price_history',1,'1405-01-01')
    assert provider_key('tsetmc','price_history',1,'1405-01-01')!=digest('price_history',1,'1405-01-01')
