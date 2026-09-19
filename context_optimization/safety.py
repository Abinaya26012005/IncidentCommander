"""Redact a copy before measuring. Integrity compares this approved LLM view."""
import math,re

BLOCKED = {'scenario','scenario_id','scenario_name','failure_type','injected_cause','expected_rca','expected_repair','expected_action','hidden_answer','test_assertion','api_key','apikey','token','authorization','password','database_password','credentials','secret','access_token','refresh_token','remediation_capabilities'}

def sanitize(value, application_id, depth=0):
    if depth > 60: raise ValueError('Context nesting exceeds safe limit')
    if isinstance(value,dict):
        if any(not isinstance(k,str) for k in value): raise ValueError('JSON requires string keys')
        if value.get('application_id') not in (None,application_id): raise ValueError('Cross-application context rejected')
        result={}
        for key,item in value.items():
            normalized=key.lower().replace('-','_')
            if normalized in BLOCKED or normalized.endswith(('_password','_secret','_api_key')) or key=='.env':continue
            result[key]=sanitize(item,application_id,depth+1)
        return result
    if isinstance(value,list):return [sanitize(x,application_id,depth+1) for x in value]
    if isinstance(value,str):
        value=re.sub(r'(?i)Bearer\s+[A-Za-z0-9._~+/=-]+','Bearer [REDACTED]',value)
        value=re.sub(r'\bsk-[A-Za-z0-9_-]{12,}','[REDACTED]',value)
        value=re.sub(r'(?im)((?:api[_-]?key|password|secret|authorization)\s*[:=]\s*)[^\s,;]+',r'\1[REDACTED]',value)
        return value
    if value is None or type(value) in (bool,int):return value
    if type(value) is float and math.isfinite(value):return value
    raise ValueError('Unsupported non-JSON context value')
