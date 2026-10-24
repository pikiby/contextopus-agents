import sys
from pathlib import Path
from types import SimpleNamespace
from threading import RLock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'module/package'))
from agents.library import library

class Catalog:
    def capture(self):
        return {str(i):{'id':str(i),'kind':'profile' if i%2 else 'team','title':'ALPHA '+str(i),
                        'description':'Text '+str(i)} for i in range(7)}
    def read(self,id):
        return dict(self.capture()[id],body={'instructions':'# Complete body'},path='profiles/a.md',revision='revision')

def test_text_filters_before_pagination_and_reads_no_index():
    service=SimpleNamespace(catalog=Catalog(),writer=RLock())
    result=library(service,'records',query='alpha',type='profile',offset=1,limit=1)
    assert result['total']==3 and result['has_more']
    assert result['records'][0]['key']==['agents','catalog','3']
    assert library(service,'record',id='1')['content']=='# Complete body'
    assert library(service,'collections')['collections'][0]['id']=='catalog'

def test_semantic_passes_type_before_selection_and_preserves_diagnostics():
    class SearchCatalog(Catalog):
        def search(self,query,kind=None):
            assert query=='alpha' and kind=='profile'
            return {'results':[dict(self.capture()['1'],distance=.2)],
                    'diagnostics':{'candidate_pool_truncated':True},'pending_count':2}
    service=SimpleNamespace(catalog=SearchCatalog(),writer=RLock())
    result=library(service,'records',query='alpha',mode='semantic',type='profile')
    assert result['records'][0]['key']==['agents','catalog','1']
    assert result['total'] is None and result['warnings']
    assert result['diagnostics']=={'candidate_pool_truncated':True}

def test_empty_type_in_ui_means_all_records():
    class SearchCatalog(Catalog):
        def search(self,query,kind=None):
            assert kind is None
            return {'results':[dict(self.capture()['1'],distance=.2)],'diagnostics':{},'pending_count':0}
    service=SimpleNamespace(catalog=SearchCatalog(),writer=RLock())
    assert library(service,'records',query='alpha',mode='semantic',type='')['records']
