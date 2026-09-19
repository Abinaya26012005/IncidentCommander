"""Full structural equality plus path-aware critical anchor counts, not NLP semantics."""
import hashlib,json

CATEGORIES={'evidence_ids':{'id','evidence_id','evidence_ids','supporting_evidence_ids'},'incident_ids':{'incident_id'},'application_ids':{'application_id'},'service_names':{'service','services','affected_services','affected_component'},'trace_ids':{'trace_id'},'span_ids':{'span_id','parent_span_id'},'request_ids':{'request_id'},'conversation_ids':{'conversation_id'},'error_codes':{'code','error','error_code'},'commit_shas':{'sha','commit','commit_sha','original_hash'},'deployment_ids':{'deployment_id'},'config_versions':{'version','prompt_version','config_version'},'dependency_names':{'dependency','dependency_name'},'statuses':{'status','healthy','ok','severity'},'timestamps':{'timestamp','created','onset','date','resolved_at'},'source_paths':{'path','file','changed_files','allowed_files'},'source_diffs':{'diff','working_diff'},'numeric_metrics':set()}

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def anchors(payload):
    found={k:{} for k in CATEGORIES}
    def walk(x,path=(),key=''):
        if isinstance(x,dict):
            for k,v in x.items():walk(v,path+(k,),k)
        elif isinstance(x,list):
            for n,v in enumerate(x):walk(v,path+(n,),key)
        else:
            for category,keys in CATEGORIES.items():
                match=key in keys
                if category=='evidence_ids':match=(isinstance(x,str) and x.startswith('E-'))
                if category=='incident_ids':match=match or (key=='id' and isinstance(x,str) and x.startswith('INC-'))
                if category=='numeric_metrics':match=type(x) in (int,float)
                if match:found[category][path]=canonical(x)
    walk(payload)
    return found

def validate(original,decoded):
    before=anchors(original);after=anchors(decoded);details={}
    for category,items in before.items():
        kept=sum(after[category].get(path)==v for path,v in items.items())
        details[category]={'required':len(items),'preserved':kept,'status':'N/A' if not items else 'PASS' if kept==len(items) else 'FAIL'}
    equivalent=canonical(original)==canonical(decoded)
    return {'status':'PASS' if equivalent else 'FAIL','round_trip_status':'PASS' if equivalent else 'FAIL','details':details,'original_sha256':hashlib.sha256(canonical(original).encode()).hexdigest(),'decoded_sha256':hashlib.sha256(canonical(decoded).encode()).hexdigest(),'method':'Canonical full structure/value/order comparison plus path-aware anchors; no semantic-quality claim'}
