"""Internal UI QA server. Production uses PostgreSQL through Docker Compose."""
import os,sys,asyncio
from pathlib import Path
base=Path(__file__).resolve().parents[1];sys.path.insert(0,str(base));os.chdir(base)
from src.config.settings import Settings
from src.repositories.database import engine_for
from src.repositories.models import metadata
from src.services.import_repository import import_history
from src.web.app import create_app
import uvicorn

settings=Settings(_env_file=None,database_url='sqlite+pysqlite:///'+str(base/'.preview.db'),
    admin_token='preview-management',request_timeout=3,max_retries=0,log_path=str(base/'.preview.log'))
engine=engine_for(settings.database_url);metadata.create_all(engine)
from sqlalchemy import select,func
from src.repositories.models import symbols
with engine.connect() as conn:count=conn.execute(select(func.count()).select_from(symbols)).scalar_one()
if not count:import_history(engine,base.parent/'Data')
app=create_app(settings,engine)
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--host',default='127.0.0.1')
parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','3000')))
args,_=parser.parse_known_args()
uvicorn.run(app,host=args.host,port=args.port)
