"""Measured deterministic utility. Integrity is an eligibility gate, never a tradeoff."""
import time,uuid
from .models import ContextOptimizationResult
from .tokenizer import tokenizer
from .token_budget import budget
from .safety import sanitize
from .profiler import profile
from .integrity_guard import validate
from .serializers import json_candidate,toon_candidate,hybrid_candidate,VERSION

# Utility weights: token saving percentage + structural suitability - fixed complexity.
# Timings are observed separately; >5s codec timeout excludes pathological candidates.
# Keeping timing out of ranking avoids nondeterministic strategy changes under CPU load.
WEIGHTS={'saving':100,'absolute_tokens_per_point':8,'uniform_toon':2,'mixed_hybrid':8,'toon_complexity':1,'hybrid_complexity':3}

def optimize(request):
    start=time.perf_counter();count,label=tokenizer(request.model_name)
    payload=sanitize(request.payload,request.application_id)
    profile_start=time.perf_counter();failures=[]
    try:properties=profile(payload,count)
    except Exception:properties={};failures.append('Profiler unavailable; validated JSON retained')
    profile_ms=(time.perf_counter()-profile_start)*1000
    profiler_failed=bool(failures)
    candidates=[];texts={};validation_ms=0;serialization_ms=0
    for strategy,serializer in [('JSON',json_candidate),('TOON',toon_candidate),('HYBRID',hybrid_candidate)]:
        if request.policy.strategy=='JSON' and strategy!='JSON':continue
        if profiler_failed and strategy!='JSON':continue
        tick=time.perf_counter()
        try:
            text,decoded=serializer(payload);encoding=(time.perf_counter()-tick)*1000;serialization_ms+=encoding
            tick=time.perf_counter();integrity=validate(payload,decoded);validation_ms+=(time.perf_counter()-tick)*1000
            candidate={'strategy':strategy,'tokens':count(text),'bytes':len(text.encode()),'encoding_time_ms':round(encoding,3),'integrity_status':integrity['status'],'round_trip_status':integrity['round_trip_status'],'integrity_details':integrity['details'],'integrity_method':integrity['method'],'valid':integrity['status']=='PASS'}
            if not candidate['valid']:failures.append(strategy+' integrity/round-trip rejected')
            texts[strategy]=text
        except Exception:
            candidate={'strategy':strategy,'tokens':None,'bytes':None,'valid':False,'integrity_status':'FAIL','round_trip_status':'FAIL','error':strategy+' serialization or validation failed'}
            failures.append(candidate['error'])
        candidates.append(candidate)
    baseline=candidates[0]
    if not baseline['valid']:raise ValueError('Safe JSON context construction failed')
    for c in candidates:
        if not c['valid']:continue
        saving=(baseline['tokens']-c['tokens'])/max(1,baseline['tokens'])
        suitability=(WEIGHTS['uniform_toon'] if c['strategy']=='TOON' and properties.get('uniform_records',0)>=4 else WEIGHTS['mixed_hybrid'] if c['strategy']=='HYBRID' and properties.get('uniform_records',0)>=4 and properties.get('git_diff_count',0) else 0)
        complexity=WEIGHTS.get(c['strategy'].lower()+'_complexity',0)
        benefit=min(WEIGHTS['saving']*saving,(baseline['tokens']-c['tokens'])/WEIGHTS['absolute_tokens_per_point'])
        c.update(token_reduction=round(saving*100,1),strategy_score=round(benefit+suitability-complexity,3),fits_context_budget=budget(request,c['tokens'])['fits_context_budget'])
    chosen=baseline;policy=request.policy
    if policy.strategy not in ('AUTO','JSON','TOON','HYBRID'):raise ValueError('Unknown context strategy')
    if not 0<=policy.minimum_expected_token_saving<=1:raise ValueError('Invalid saving threshold')
    reasons=[]
    if failures:
        reasons.append('Candidate/measurement failure: safe JSON fallback')
    elif policy.strategy!='AUTO':
        chosen=next(c for c in candidates if c['strategy']==policy.strategy)
        reasons.append('Explicit '+policy.strategy+' policy; measured and validated')
    else:
        eligible=[c for c in candidates if c['valid'] and (c['strategy']=='JSON' or (baseline['tokens']-c['tokens'])/max(1,baseline['tokens'])>=policy.minimum_expected_token_saving)]
        if baseline['fits_context_budget'] is False:
            fitting=[c for c in candidates if c['valid'] and c['fits_context_budget'] is True]
            if fitting:eligible=fitting;reasons.append('Context budget pressure: a fitting candidate takes priority')
        chosen=max(eligible,key=lambda c:(c['strategy_score'],-c['tokens'],c['strategy']=='JSON'))
        reasons.append('Highest deterministic utility among valid measured candidates')
        if chosen['strategy']=='JSON':reasons.append('Alternative savings below threshold or utility does not justify format complexity')
    guard=budget(request,chosen['tokens'])
    if guard['fits_context_budget'] is False:reasons.append('No selected safe representation fits; provider send blocked, no evidence truncated')
    reasons.extend([f"{properties.get('uniform_records',0)} uniform records; {properties.get('repeated_key_overhead_bytes',0)} repeated-key bytes",f"Minimum saving policy: {policy.minimum_expected_token_saving*100:g}%"])
    fallback=bool(failures) or (chosen['strategy']=='JSON' and policy.strategy=='AUTO')
    elapsed=(time.perf_counter()-start)*1000
    metrics={'original_tokens':baseline['tokens'],'optimized_tokens':chosen['tokens'],'token_reduction':chosen['token_reduction'],'original_bytes':baseline['bytes'],'optimized_bytes':chosen['bytes'],'byte_reduction':round((baseline['bytes']-chosen['bytes'])/max(1,baseline['bytes'])*100,1),'encoding_time_ms':chosen['encoding_time_ms'],'profile_time_ms':round(profile_ms,3),'serialization_time_ms':round(serialization_ms,3),'validation_time_ms':round(validation_ms,3),'total_optimization_time_ms':round(elapsed,3),'available_context_budget':guard['available_context_budget'],'fits_context_budget':guard['fits_context_budget'],'budget':guard,'strategy_score':chosen['strategy_score'],'strategy_reasons':reasons,'integrity_status':chosen['integrity_status'],'round_trip_status':chosen['round_trip_status'],'integrity_details':chosen['integrity_details'],'integrity_method':chosen['integrity_method'],'fallback_strategy':'JSON' if fallback else None,'fallback_triggered':fallback,'fallback_reason':'; '.join(failures) if failures else reasons[1] if fallback else None,'candidate_results':candidates,'serializer_version':VERSION,'tokenizer_name':label,'profile':properties,'delivery':'PREPARED — NOT SENT','metadata':request.metadata}
    return ContextOptimizationResult(uuid.uuid4().hex,request.purpose,request.application_id,request.incident_id,time.time(),chosen['strategy'],texts[chosen['strategy']],metrics)
