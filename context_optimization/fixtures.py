"""Synthetic benchmark inputs, clearly separate from incident evidence."""
def uniform_records(n=100):
    return [{'id':f'E-{i:03}','service':'payment-service','severity':'ERROR','status':'failed','error_code':'POOL_EXHAUSTED','latency_ms':420+i%8,'timestamp':1789770000+i} for i in range(n)]

def fixtures():
    return {'small':{'healthy':True},'uniform':uniform_records(), 'mixed':{'incident':{'application_id':'payflow','incident_id':'INC-BENCH','severity':'SEV-2'},'observations':uniform_records(),'source':{'path':'payment_logic.py','sha':'abc123','diff':'@@ -1,3 +1,2 @@\n-    finally:\n-        pool.release(connection)\n+    return result\n'},'history':[{'id':f'INC-H{i}','service':'payment-service','status':'resolved','resolution':'Release connection'} for i in range(20)],'runbook':{'title':'Investigate checkout','prose':'Compare independent dependency probes with failed request spans. Preserve the exact source diff before considering changes.'},'irregular':[{f'key{i}':{'x':i,'flags':[True,None,False]}} for i in range(20)]}}
