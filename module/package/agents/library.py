"""Catalog browsing through file-authoritative module APIs."""
import json
import re


def library(service, action, collection=None, query='', mode='text', type=None, offset=0, limit=50, id=None):
    if action == 'collections':
        return {'collections': [{'id':'catalog','title':'Agents and teams'}]}
    if collection and collection != 'catalog':
        raise ValueError('Unknown Agents collection')
    type = type or None
    catalog = service.catalog
    with service.writer:
        records = catalog.capture()
        def label(record):
            return {'key':['agents','catalog',record['id']], 'title':record['title'],
                    'description':record['description'], 'type':record['kind']}
        if action == 'record':
            record = catalog.read(id)
            links = []
            if record['kind'] == 'team':
                for role, binding in record['body']['roles'].items():
                    target = records.get(binding.get('profile'))
                    if target:
                        links.append({**label(target), 'description':role+': '+target['description']})
                    else:
                        links.append({'title':role,'reference':binding.get('profile',binding.get('session','')),'unavailable':True})
            references = re.findall(r'\[\[[^]\n]+\]\]',record['body'].get('instructions',''))
            seen = {tuple(item.get('key',[item.get('reference','')])) for item in links}
            for reference in dict.fromkeys(references):
                target = catalog.resolve_reference(reference,records=records)
                if target:
                    item = label(records[target])
                else:
                    try:
                        name = reference[2:-2].split('|',1)[0].removeprefix('core/instructions/')
                        document = service.core.instructions.read(reference=name)
                        item = {'key':['core','instructions',document['id']], 'title':document['title'],
                                'description':document['description']}
                    except (ValueError, RuntimeError, OSError, AttributeError):
                        item = {'title':reference[2:-2].split('|')[-1], 'reference':reference,'unavailable':True}
                key = tuple(item.get('key',[reference]))
                if key not in seen:
                    links.append(item)
                    seen.add(key)
            return {**label(record),'content':record['body'].get('instructions',''),
                    'metadata':record['body'], 'links':links, 'path':record['path'], 'revision':record['revision']}
        if action != 'records':
            raise ValueError('Unknown library action')
        types = sorted({record['kind'] for record in records.values()})
        values = [label(record) for _,record in sorted(records.items()) if not type or record['kind']==type]
    if mode == 'semantic' and query.strip():
        found = catalog.search(query,kind=type)
        values = [label({**item,'kind':item['kind']}) | {'distance':item['distance']} for item in found['results']]
        return {'records':values[offset:offset+limit], 'total':None, 'has_more':offset+limit<len(values),
                'types':types, 'diagnostics':found['diagnostics'],
                'warnings': ([f"{found['pending_count']} records await indexing"] if found.get('pending_count') else [])}
    values.sort(key=lambda item:(item['title'].casefold(),item['key']))
    if query:
        needle = query.casefold()
        values = [item for item in values if needle in (item['title']+'\n'+item['description']).casefold()]
    return {'records':values[offset:offset+limit], 'total':len(values),
            'has_more':offset+limit<len(values), 'types':types}
