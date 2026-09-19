import json
from collections import Counter

def uniform(value):
    return isinstance(value,list) and len(value)>=2 and all(isinstance(x,dict) and x and set(x)==set(value[0]) and all(not isinstance(v,(dict,list)) for v in x.values()) for x in value)

def profile(payload, count):
    keys=Counter();types=Counter();stats=Counter();texts=[];distribution=Counter()
    def walk(x,depth=0):
        stats['maximum_nesting_depth']=max(stats['maximum_nesting_depth'],depth)
        types['nested' if isinstance(x,(list,dict)) else 'scalar']+=1
        if isinstance(x,dict):
            stats['object_count']+=1;keys.update(x.keys())
            if 'source_type' in x:distribution[str(x['source_type'])]+=1;stats['evidence_objects']+=1
            for k,v in x.items():
                if k in ('records','logs','spans','samples','matches') and isinstance(v,list):stats[k+'_count']+=len(v)
                if 'diff' in k and isinstance(v,str) and v:stats['git_diff_count']+=1
                walk(v,depth+1)
        elif isinstance(x,list):
            stats['array_count']+=1
            if uniform(x):stats['uniform_arrays']+=1;stats['uniform_records']+=len(x)
            for v in x:walk(v,depth+1)
        elif isinstance(x,str):texts.append(len(x))
    walk(payload)
    encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    total=sum(types.values()) or 1
    return {**dict(stats),'serialized_bytes':len(encoded.encode()),'token_count':count(encoded),'repeated_key_overhead_bytes':sum((n-1)*len(json.dumps(k).encode()) for k,n in keys.items()),'structural_repetition':round(sum(n-1 for n in keys.values())/max(1,sum(keys.values())),4),'average_text_length':round(sum(texts)/max(1,len(texts)),2),'schema_complexity':len(keys)+stats['maximum_nesting_depth'],'scalar_percentage':round(types['scalar']/total*100,1),'nested_percentage':round(types['nested']/total*100,1),'evidence_type_distribution':dict(distribution),'log_records':stats['logs_count']+stats['records_count'],'metric_records':stats['samples_count']+distribution['METRIC'],'trace_records':stats['spans_count']+distribution['TRACE'],'health_dependency_records':distribution['DEPENDENCY']+distribution['DATABASE'],'source_change_records':distribution['GIT']+distribution['CONFIG']+distribution['DEPLOYMENT'],'memory_runbook_records':stats['matches_count']+distribution['RUNBOOK']}
