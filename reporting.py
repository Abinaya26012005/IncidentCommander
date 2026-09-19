"""Measured recovery comparisons and one application-aware report representation."""
import json
from datetime import datetime,timezone

def summarize(rows):
    lat=sorted(r.get('latency',0) for r in rows);n=len(rows);failed=sum(not bool(r.get('ok')) for r in rows)
    return {'requests':n,'failures':failed,'success_rate':round(100*(n-failed)/n,1) if n else None,'error_rate':round(100*failed/n,1) if n else None,'p95':lat[min(n-1,int(n*.95))] if n else None}

def recovery(inc):
    before=next((e['metadata'] for e in inc.get('evidence',[]) if e['source_type']=='METRIC'),{})
    after=(inc.get('verification') or {}).get('measured',{})
    if not after:return []
    rows=[]
    def add(label,b,a,unit=''):
        fmt=lambda v:'Not observed' if v is None else str(v)+unit
        rows.append({'label':label,'before':fmt(b),'after':fmt(a)})
    if before.get('channels'):
        for channel in ('voice','chat'):
            b=before['channels'][channel];a=after.get('channels',{}).get(channel,{})
            add(channel.title()+' success',b.get('success_rate') if b.get('requests') else None,a.get('success_rate'),'%')
        add('Pipeline p95',before.get('p95') if before.get('requests') else None,after.get('p95'),' ms')
        health=next((e['metadata'].get('services',{}) for e in inc['evidence'] if e['source_type']=='DEPENDENCY'),{})
        for name,h in after.get('dependencies',{}).items():
            b=health.get(name);state=lambda v:None if v is None else 'HEALTHY' if v.get('healthy') else 'UNHEALTHY'
            add(name,state(b),state(h))
    else:
        n=before.get('requests',0);errors=before.get('error_rate')
        add('Success',round(100-errors,1) if n and errors is not None else None,after.get('success_rate'),'%')
        add('Errors',errors if n else None,after.get('error_rate'),'%')
        add('Payment p95',before.get('p95') if n else None,after.get('p95'),' ms')
        add('DB pool',before.get('pool',{}).get('utilization'),after.get('pool_utilization'),'%')
        db=next((e['metadata'].get('healthy') for e in inc['evidence'] if e['source_type']=='DATABASE'),None)
        bank=next((e['metadata'].get('healthy') for e in inc['evidence'] if e['source_type']=='DEPENDENCY'),None)
        state=lambda h:'HEALTHY' if h is True else 'UNHEALTHY' if h is False else None
        add('Database health',state(db),state(after.get('database_healthy')))
        add('Bank health · simulated provider',state(bank),state(after.get('bank_healthy')))
    return rows

def recommendations(inc):
    r=inc.get('rca') or {};component=r.get('affected_component','affected service');action=(inc.get('plan') or {}).get('action') or r.get('action')
    tips=[f'Add regression coverage for the observed {component} failure and verify the complete affected customer path after changes.']
    if action=='restore_cleanup':tips+=['Test connection release on both successful and exceptional paths; monitor checked-out pool capacity.']
    elif component=='tts-service':tips+=['Alert on speech-delivery errors separately from successful text generation; verify voice and chat independently.']
    elif component=='stt-service':tips+=['Track recognition latency against its budget and compare voice latency with chat.']
    elif component=='knowledge-service':tips+=['Add retrieval availability and required-context checks before promoting changes.']
    elif component=='llm-service':tips+=['Validate response contracts and prompt configuration against representative conversations before deployment.']
    else:tips+=[f'Review source/config changes affecting {component}; monitor its failure and latency boundaries.']
    return tips

def stamp(value):return datetime.fromtimestamp(value,timezone.utc).isoformat() if value else 'Not recorded'

def report(inc):
    r=inc.get('rca') or {};p=inc.get('plan') or {};v=inc.get('verification') or {};evidence=inc.get('evidence',[])
    m=next((e['metadata'] for e in evidence if e['source_type']=='METRIC'),{})
    duration=round(inc['resolved_at']-inc['created'],2) if inc.get('resolved_at') else None
    sections=[]
    def add(title,body):sections.append({'title':title,'body':str(body)})
    add('Incident',f"{inc['id']} · {inc['status']}\nSeverity: {inc.get('severity','Not recorded')} (demo classification)")
    add('Application',inc.get('application_name',inc['application_id']))
    add('Customer / user impact',f"Affected services: {', '.join(inc.get('affected_services',[])) or 'Under investigation'}\nAffected capabilities: {', '.join(inc.get('affected_capabilities',[])) or 'Application request path'}\nAt evidence collection: {m.get('failures','Not observed')} failed / {m.get('requests','Not observed')} recent requests. These are request counts, not unique affected users.")
    add('Timeline','\n'.join(stamp(e['timestamp'])+' · '+e['text'] for e in inc.get('timeline',[])))
    add('Root cause',r.get('explanation','Not established')+'\nReasoning mode: '+r.get('ai_mode',r.get('engine','Not recorded'))+'\nEvidence strength: '+str(r.get('confidence','Not recorded'))+'/100 — heuristic, not statistical probability.')
    add('Evidence','\n'.join(e['id']+' ['+e['source_type']+'] '+e['summary'] for e in evidence))
    changes=[]
    for e in evidence:
        if e['source_type'] in ('GIT','CONFIG','DEPLOYMENT'):
            data=e['metadata'];detail=(data.get('local',{}).get('working_diff') or data.get('diff') or 'No diff observed') if e['source_type']=='GIT' else json.dumps(data,indent=2)
            changes.append(e['id']+' ['+e['source_type']+'] '+detail)
    add('Relevant source / config / deployment change','\n\n'.join(changes) or 'No changes observed')
    add('Eliminated hypotheses','\n'.join(a['title']+': '+a['reason']+' ['+', '.join(a.get('evidence_ids',[a.get('evidence','')]))+']' for a in r.get('alternatives',[])) or 'None established')
    add('Remediation',p.get('title','No approved proposal')+'\nPatch source: '+p.get('patch_source','Not recorded')+'\n'+p.get('diff','No patch'))
    add('Risk',p.get('risk','Not assessed')+'\n'+p.get('policy','No executable change authorized'))
    approvals=[e for e in inc.get('timeline',[]) if e.get('kind')=='approval']
    add('Approval','\n'.join(stamp(e['timestamp'])+' · '+e['text'] for e in approvals) or 'Not approved')
    add('Verification',('Recovery verified' if v.get('passed') else 'Recovery not verified; incident remains open')+'\n'+json.dumps(v,indent=2))
    comparison=recovery(inc)
    add('Recovery metrics','Before = saved evidence window. After = fresh verification requests/probes.\n'+'\n'.join(x['label']+': '+x['before']+' → '+x['after'] for x in comparison) if comparison else 'No measured before/after comparison yet')
    add('MTTR / duration',(str(duration)+' seconds from detection to verified recovery') if duration is not None else 'Not resolved; final duration unavailable')
    add('Prevention recommendations','\n'.join('- '+x for x in recommendations(inc)))
    add('Provider disclosure','Local external bank and speech/model providers are simulated. Reasoning-provider mode and patch provenance are recorded separately. This is a local sandbox result, not a production reliability guarantee.')
    context=next((r for r in reversed(inc.get('context_optimization',[])) if r['purpose']=='RCA'),None)
    if context:add('AI Context Optimization',f"Strategy: {context['selected_strategy']}\nTokens: {context.get('original_tokens','N/A')} → {context.get('optimized_tokens','N/A')}\nMeasured reduction: {context.get('token_reduction','N/A')}%\nEvidence integrity: {context.get('integrity_status','N/A')}\nTokenizer: {context.get('tokenizer_name','N/A')}\nFallback: {context.get('fallback_reason') or 'None'}\n{context.get('delivery','Not sent')}")
    if inc.get('escalation'):add('Escalation',inc['escalation']['note']+'\n'+stamp(inc['escalation']['timestamp']))
    title=inc['id']+' · '+r.get('title','Incident report')
    return {'title':title,'application_id':inc['application_id'],'status':inc['status'],'sections':sections,'markdown':'# '+title+'\n\n'+'\n\n'.join('## '+s['title']+'\n'+s['body'] for s in sections)}
