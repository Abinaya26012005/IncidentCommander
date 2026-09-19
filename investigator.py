"""Evidence-only diagnosis. This module cannot access fault injection controls."""
import json, os, re, urllib.request

RUNBOOKS=[
 {'id':'RB-001','title':'Connection pool exhaustion','terms':['DB_POOL_EXHAUSTED','pool','cleanup'], 'steps':['Compare pool saturation with database health.','Inspect connection ownership in the deployed source.','Restore cleanup, recycle the sandbox pool, and run fresh transactions.']},
 {'id':'RB-002','title':'Payment provider unavailable','terms':['BANK_UNAVAILABLE','bank'], 'steps':['Check provider health independently.','Do not roll back healthy application code.','Restore the sandbox provider, then verify payment completion.']},
 {'id':'RB-003','title':'Provider timeout budget','terms':['BANK_TIMEOUT','timeout'], 'steps':['Compare configured timeout with observed provider latency.','Restore the previous timeout budget.','Verify successful payments and latency.']},
 {'id':'RB-004','title':'Slow provider investigation','terms':['BANK_TIMEOUT','latency'], 'steps':['Measure the provider independently.','Compare bank spans against local processing and timeout budget.','Only restore a sandbox provider setting with approval; escalate a real external outage.']},
 {'id':'RB-005','title':'Database dependency unavailable','terms':['DB_UNAVAILABLE'], 'steps':['Probe database health independently of the application pool.','Separate availability failures from capacity exhaustion.','Restore the sandbox dependency and verify durable payments.']},
 {'id':'RB-006','title':'Unexpected payment code regression','terms':['PAYMENT_INTERNAL_ERROR','SOURCE_RELOAD_FAILED','PAYMENT_RETURN_CONTRACT'], 'steps':['Locate the exception and source frame.','Correlate local working changes and reload time with impact.','Validate a minimal patch; escalate if evidence or validation is insufficient.']},
 {'id':'RB-007','title':'Order service blast radius','terms':['ORDER_UNAVAILABLE'], 'steps':['Find the failing order span.','Check payment and bank health separately.','Verify new orders and successful checkout after an approved repair.']},
 {'id':'RB-008','title':'Bank endpoint configuration','terms':['BANK_ENDPOINT_NOT_FOUND'], 'steps':['Probe the known local bank endpoint.','Compare it with the configured request path.','Review the endpoint diff and verify new charges.']},
 {'id':'RB-009','title':'Pool sizing under concurrency','terms':['DB_POOL_EXHAUSTED','pool_size'], 'steps':['Check configured capacity and cleanup on success and exception paths.','Distinguish transient contention from unreleased connections.','Restore bounded capacity and repeat concurrent checkout traffic.']},
 {'id':'RB-010','title':'Gateway target routing','terms':['GATEWAY_ROUTE_NOT_FOUND'], 'steps':['Check payment health independently.','Inspect gateway target configuration and 404 traces.','Validate the local route and verify checkout end to end.']},
 {'id':'RB-011','title':'Local processing latency','terms':['payment-processing','processing_delay_ms'], 'steps':['Compare processing spans with bank and database latency.','Inspect recent local processing settings.','Verify fresh p95 latency after the approved change.']}
]

def diagnose(evidence):
    applications={e['application_id'] for e in evidence if e.get('application_id')}
    incidents={e['incident_id'] for e in evidence if e.get('incident_id')}
    if len(applications)>1 or len(incidents)>1:raise ValueError('Mixed application or incident evidence rejected')
    by={e['source_type']:e for e in evidence};data={k:v['metadata'] for k,v in by.items()}
    logs=data.get('LOG',{}).get('records',[]);codes={r['code'] for r in logs}
    source=data.get('GIT',{}).get('source','');dep=data.get('DEPENDENCY',{});bank=dep.get('healthy');db=data.get('DATABASE',{}).get('healthy')
    pool=data.get('DATABASE',{}).get('pool',{});config=data.get('CONFIG',{});traces=data.get('TRACE',{}).get('traces',[])
    action=None;ruled=[];component='unknown';title='Insufficient evidence';explanation='No supported cause or safe repair has been established. Gather more observations or escalate to an engineer.'
    if 'DB_POOL_EXHAUSTED' in codes and db and 'pool.release(connection)' not in source and pool.get('utilization')==100:
        title='Unreleased connections exhausted the payment pool';explanation='Failed requests stop at connection acquisition. The database is healthy, but the deployed source no longer returns acquired connections to the pool.';action='restore_cleanup';component='payment-service'
    elif 'DB_POOL_EXHAUSTED' in codes and db and config.get('pool_size')==1 and 'pool.release(connection)' in source:
        title='The connection pool is too small for concurrent checkout traffic';explanation='Acquisition timeouts occurred with a one-connection configuration while source cleanup remains present. Contention, rather than a missing release, explains this evidence.';action='restore_pool';component='payment-service'
    elif 'DB_UNAVAILABLE' in codes and db is False:
        title='The database dependency is unavailable';explanation='Database health and request acquisition both fail. This is an unavailable dependency, not merely a saturated application pool.';action='restore_database';component='database'
    elif 'BANK_TIMEOUT' in codes and bank and dep.get('latency_ms',0)>500 and config.get('bank_timeout_ms',0)>=500:
        title='The bank provider has become too slow';explanation='An independent provider probe and failed bank spans show elevated response time. The application timeout remains at its normal budget.';action='restore_latency';component='bank-api'
    elif 'BANK_TIMEOUT' in codes and bank and config.get('bank_timeout_ms',800)<dep.get('latency_ms',90) and dep.get('latency_ms',90)<500:
        title='The payment timeout is shorter than the bank response';explanation='The provider responds normally, but the configured timeout expires earlier. Configuration and request traces support a timeout-budget regression.';action='restore_timeout';component='payment-service'
    elif 'BANK_UNAVAILABLE' in codes and bank is False:
        title='The sandbox bank is rejecting payment requests';explanation='Failed traces end at the bank API, and an independent health probe confirms provider unavailability. Restarting the database would not address this evidence.';action='restore_bank';component='bank-api'
    elif 'BANK_ENDPOINT_NOT_FOUND' in codes and bank and config.get('bank_path')!='/charge':
        title='Payment requests are sent to the wrong bank endpoint';explanation='The correct bank endpoint is healthy, while the configured path returns HTTP 404. The routing change explains the mismatch.';action='restore_endpoint';component='payment-service'
    elif 'ORDER_UNAVAILABLE' in codes and dep.get('order_healthy') is False:
        title='Order creation fails before the payment service is called';explanation='Checkout traces terminate at Order Service. Payment service health remains independently observable; the blast radius is order creation and checkout.';action='restore_order';component='order-service'
    elif 'GATEWAY_ROUTE_NOT_FOUND' in codes and dep.get('payment_healthy') and config.get('gateway_path')!='/pay':
        title='The gateway is routing payments to a missing endpoint';explanation='Gateway requests receive HTTP 404 while the payment service health probe succeeds. The gateway target path changed.';action='restore_gateway';component='api-gateway'
    elif 'PAYMENT_INTERNAL_ERROR' in codes and 'optional = None' in source and "optional.get('reference')" in source and any(r.get('detail',{}).get('exception')=='AttributeError' for r in logs if r.get('detail')):
        title='An optional field is dereferenced while it is None';explanation='An AttributeError is localized to payment_logic.py. The observed source calls get on a None value before the bank request. Dependency probes remain available.';action='restore_code';component='payment-service'
    elif any(s['service']=='payment-processing' and s['ms']>=500 for t in traces for s in t['spans']) and bank and db:
        title='Payment processing adds excessive local latency';explanation='The local payment-processing span dominates request latency while bank and database probes remain healthy.';action='restore_processing';component='payment-service'
    elif {'PAYMENT_INTERNAL_ERROR','PAYMENT_RETURN_CONTRACT','SOURCE_RELOAD_FAILED'} & codes:
        title='Unexpected local payment regression needs review';explanation='Runtime failures are localized to the payment code or its reload. The source diff and exception are available, but no deterministic repair is established. Use configured AI analysis or engineer review.';component='payment-service'
    # Generic dependency correlation: actual failing spans + matching logs + independent probes.
    # This works for any adapter exposing the normalized service-health map, without application IDs or scenario labels.
    services=dep.get('services',{})
    for name,health in services.items():
        observed=[s for trace in traces for s in trace.get('spans',[]) if s['service']==name]
        errors=[r for r in logs if r.get('service')==name and r.get('severity')=='ERROR']
        label=health.get('display_name',name.replace('-',' '))
        failed=any(s['status']=='error' for s in observed)
        if not action and failed and errors and health.get('healthy') is False:
            component=name;action='restore_dependency';title=label+' dependency failure';explanation=f'{label} returned failures in actual request spans and matching service logs. An independent health probe also failed. Earlier successful stages localize the interruption to this dependency.'
        elif not action and failed and any(r.get('code')=='OUTPUT_VALIDATION_FAILED' for r in errors) and health.get('healthy') and config.get('prompt_version')!='v1' and (data.get('GIT',{}).get('diff') or data.get('GIT',{}).get('local',{}).get('working_diff')):
            component=name;action='restore_configuration';title='Recent configuration caused invalid generated responses';explanation='Generation returned an invalid response, while the provider health probe succeeded. A changed prompt version and the observed output-validation error support a configuration regression rather than a provider outage.'
        elif not action and observed and health.get('healthy') and max(s['ms'] for s in observed)>=health.get('latency_budget_ms',500):
            component=name;action='restore_latency';title=label+' latency is degrading the affected channel';explanation=f'{label} spans exceed the independently reported latency budget. Dependency availability alone does not establish timely responses; compare affected channel requests with the healthy channel.'
        if health.get('healthy'):
            success=any(s['status']=='ok' and s.get('output_valid',True) for s in observed)
            ruled.append({'title':label+' outage','reason':'Independent health probe succeeded.'+(' Actual request spans also completed successfully with valid output.' if success else ' No successful request span is assumed from health alone.'),'evidence':by['DEPENDENCY']['id']})
    if bank:ruled.append({'title':'Bank outage','reason':'An independent bank probe succeeded. Latency is assessed separately.','evidence':by['DEPENDENCY']['id']})
    if db:ruled.append({'title':'Database server outage','reason':'An independent database health probe succeeded. Pool capacity is assessed separately.','evidence':by['DATABASE']['id']})
    if 'pool.release(connection)' in source:ruled.append({'title':'Missing cleanup','reason':'A release call is present; this alone does not prove every path releases correctly.','evidence':by['GIT']['id']})
    factors=[]
    if codes:factors.append({'factor':'Direct error observations','weight':20,'evidence':by['LOG']['id']})
    if traces:factors.append({'factor':'Request trace localization','weight':20,'evidence':by['TRACE']['id']})
    if data.get('METRIC',{}).get('requests'):factors.append({'factor':'Measured request degradation','weight':15,'evidence':by['METRIC']['id']})
    if 'DEPENDENCY' in by and ('DATABASE' in by or 'HEALTH' in by):factors.append({'factor':'Independent dependency probes','weight':15,'evidence':by['DEPENDENCY']['id']})
    git=data.get('GIT',{});diff=git.get('local',{}).get('working_diff') or git.get('diff','')
    if diff:factors.append({'factor':'Source or configuration change available','weight':10,'evidence':by['GIT']['id']})
    deploy=data.get('DEPLOYMENT',{}).get('timestamp',0)
    if traces and 0<=min(t['timestamp'] for t in traces)-deploy<120:factors.append({'factor':'Reload preceded observed impact','weight':10,'evidence':by['DEPLOYMENT']['id']})
    if data.get('RUNBOOK',{}).get('matched'):factors.append({'factor':'Relevant runbook match','weight':5,'evidence':by['RUNBOOK']['id']})
    score=min(95,sum(f['weight'] for f in factors)) if action else min(55,sum(f['weight'] for f in factors))
    ids=list(dict.fromkeys(f['evidence'] for f in factors))
    channels=sorted({t['channel'] for t in traces if t.get('channel') and any(s['service']==component and (s['status']=='error' or s['ms']>=500) for s in t.get('spans',[]))})
    return {'title':title,'explanation':explanation,'confidence':score,'confidence_label':'Python evidence score; not a probability','confidence_factors':factors,'citations':ids,'action':action,'alternatives':ruled,'affected_component':component,'affected_capabilities':channels,'status':'SUPPORTED' if action else 'INSUFFICIENT_EVIDENCE','requires_more_evidence':not bool(action),'engine':'Offline evidence engine'}

def validate_analysis(value, valid_ids):
    if not isinstance(value,dict) or set(value)!= {'title','explanation','citations'}: raise ValueError('Invalid analysis shape')
    if not all(isinstance(value[k],str) and 0<len(value[k])<=3000 for k in ('title','explanation')): raise ValueError('Invalid text')
    if not isinstance(value['citations'],list) or not value['citations'] or not all(isinstance(x,str) and x in valid_ids for x in value['citations']): raise ValueError('Unknown evidence citation')
    inline=set(re.findall(r'E-\d+',value['title']+' '+value['explanation']))
    if not inline.issubset(valid_ids): raise ValueError('Unknown inline evidence citation')
    return value

def validate_hypothesis(value,valid_ids):
    expected={'primary_hypothesis','affected_component','suspected_file','suspected_change','supporting_evidence_ids','contradicting_evidence_ids','alternative_hypotheses','recommended_action','requires_more_evidence','patch'}
    if not isinstance(value,dict) or set(value)!=expected:raise ValueError('Invalid hypothesis shape')
    for field in ('primary_hypothesis','affected_component','suspected_file','suspected_change','recommended_action'):
        if not isinstance(value[field],str) or len(value[field])>3000:raise ValueError('Invalid hypothesis field')
    if type(value['requires_more_evidence']) is not bool:raise ValueError('Invalid uncertainty flag')
    for field in ('supporting_evidence_ids','contradicting_evidence_ids'):
        if not isinstance(value[field],list) or any(x not in valid_ids for x in value[field]):raise ValueError('Unknown evidence ID')
    if not isinstance(value['alternative_hypotheses'],list) or any(not isinstance(x,str) for x in value['alternative_hypotheses']):raise ValueError('Invalid alternatives')
    if not isinstance(value['patch'],list) or len(value['patch'])>2:raise ValueError('Invalid patch list')
    if value['patch'] and (value['requires_more_evidence'] or not value['supporting_evidence_ids']):raise ValueError('Unsupported patch')
    inline=set(re.findall(r'E-\d+',json.dumps(value)))
    if not inline.issubset(valid_ids):raise ValueError('Unknown inline evidence ID')
    return value


def enrich_with_ai(evidence,result,context=None):
    from ai_reasoning import reason
    return reason(evidence,result,context or {})
