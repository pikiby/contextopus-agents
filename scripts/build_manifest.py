"""Build the checked-in operation manifest from shared JSON-schema pieces."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def obj(properties=None, required=()):
    return {'type':'object','properties':properties or {},'required':list(required),'additionalProperties':False}
def string(maximum=8192):
    return {'type':'string','minLength':1,'maxLength':maximum}
def enum(*values): return {'enum':list(values)}
ID=string(128)
TEXT=string(32768)
BOOL={'type':'boolean'}
PAGE={'offset':{'type':'integer','minimum':0},'limit':{'type':'integer','minimum':1,'maximum':100}}
BODY = {
    'type': 'object', 'maxProperties': 8,
    'description': 'Content inside record.body. Profiles require model and allow instructions/settings; teams require roles and allow instructions.',
    'properties': {
        'model': {'type': 'string', 'description': 'Required for a profile: the user-selected model. Located at record.body.model.'},
        'instructions': {'type': 'string', 'description': 'Optional complete executor or team instructions, at record.body.instructions.'},
        'settings': {'type': 'object', 'description': 'Optional profile settings; preserve the existing settings when updating.'},
        'roles': {'type': 'object', 'description': 'Required for a team: nonempty mapping of role names to objects containing profile (an existing profile ID).'},
    },
}
RECORD=obj({'id':ID,'kind':enum('profile','team'),'title':string(256),'description':string(2048),'body':BODY},['id','kind','title','description','body'])
RECORD['description'] = 'Required nested record object. Put id, kind, title, description and body here, not directly in arguments. Read results include other metadata; do not copy that metadata into record.'

operations=[]
def op(name,kind,description,properties=None,required=()):
    operations.append({'name':'agents.'+name,'kind':kind,'description':description,'service':True,'arguments_schema':obj(properties,required),'timeout':120})
op('library','query','Browse authoritative profiles and teams without launching agents.',{'action': {'enum': ['collections', 'records', 'record']}, 'collection': {'type': 'string'}, 'query': {'type': 'string'}, 'mode': {'enum': ['text', 'semantic']}, 'type': {'type': 'string'}, 'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}, 'id': {'type': 'string'}},['action'])
op('status','query','Inspect catalog workers, source errors and pending RAG jobs.')
op('instructions_read','query','Read the complete user instruction for the main agent; keep it separate from profiles and procedures.')
op('instructions_save','execute','Save explicitly requested main-agent instructions after showing the actual text; expected revision protects concurrent edits.',{'content':{'type':'string','maxLength':262144},'expected_revision':ID},['content','expected_revision'])
op('team_read','query','Read a team and its member purposes before choosing a role; does not launch agents.',{'team':ID},['team'])
op('record_save','execute','Save a profile or team. arguments contains record and optional expected_revision; all record fields belong inside record, and model/instructions/settings or roles belong inside record.body. Read this signature before the first save. Writes authoritative Markdown; SQL/RAG are derived asynchronously.',{'record':RECORD,'expected_revision':{'type':['string','null'],'description':'Sibling of record in arguments, not a record/body field. Supply the current full-file revision for an update; omit or use null only for a new ID.'}},['record'])
op('profile_delete','execute','Delete an unreferenced source profile and shared RAG at the expected full-file revision. Native definitions are managed through agents/install.',{'id':ID,'expected_revision':ID},['id','expected_revision'])
op('catalog_migration_plan','query','Inspect explicit legacy SQL/config migration without writing source files.')
op('catalog_migrate','execute','Export legacy catalog SQL to Markdown and legacy rules to Core instructions; retain legacy backup. Never runs on startup.',{'expected_revision':ID},['expected_revision'])
op('read','query','Read the complete current profile or team.',{'id':ID},['id'])
op('list','query','List catalog descriptions without loading full profiles.',{'kind':enum('profile','team'),**PAGE})
op('search','query','Semantic discovery using inherited Core selection and diagnostics. Read selected IDs before use.',{'query':TEXT,'kind':enum('profile','team'),'selection':{'type':'object'}},['query'])
op('team_resolve','query','Resolve one named role to a complete profile.',{'team':ID,'role':ID},['team','role'])
manifest={'id':'agents','version':'0.4.0','core_requires':'>=1.7,<2','rag':True,'service':{'factory':'worker.py:create_service','ready_timeout':15,'stop_timeout':40},'storage':{'engine':'sqlite','schema_version':1,'migrations':'migrations','compatible_versions':{'min':1,'max':1}},'procedures':'procedures','skills':'skills','operations':operations}
(ROOT/'module/module.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
