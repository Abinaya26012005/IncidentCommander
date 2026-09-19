"""Application boundary and shared evidence/policy contracts. No fault-label diagnosis."""
from abc import ABC,abstractmethod
from dataclasses import dataclass,asdict,field
import os,uuid
from common import request

@dataclass
class MonitoredApplication:
 id:str
 name:str
 type:str
 description:str
 url:str
 services:list
 topology:list
 capabilities:list
 evidence_providers:list
 remediation_capabilities:list
 environment:str='local sandbox'
 status:str='UNKNOWN'
 ui:dict=field(default_factory=dict)
 def to_dict(self):return asdict(self)

class ApplicationAdapter(ABC):
 """Implement this boundary to onboard an application into the SAME ResponseEngine."""
 slow_ms=500
 verification_description='Fresh requests and independent health probes must pass.'
 runbooks=[]
 scenarios=()
 seed_history=[]
 @abstractmethod
 def telemetry(self):pass
 @abstractmethod
 def collect(self,inc,t,history):pass
 @abstractmethod
 def propose(self,rca,t):pass
 @abstractmethod
 def probe(self,origin='manual'):pass
 @abstractmethod
 def verify(self,inc,emit):pass
 def get_services(self):return self.application.services
 def get_topology(self):return self.application.topology
 def get_metrics(self):return self.telemetry()['metrics']
 def get_logs(self):return self.telemetry()['logs']
 def get_traces(self):return self.telemetry()['events']
 def get_recent_changes(self):return self.telemetry()['local_source']
 def get_config_changes(self):return self.telemetry()['config']
 def get_deployments(self):return self.telemetry()['deployments']
 def get_allowed_remediations(self):return self.application.remediation_capabilities
 def get_verification_strategy(self):return self.verify
 def validate_patch(self,edits):return request(self.control_url+'/patch/validate',{'edits':edits},timeout=15)
 def apply(self,plan):
  if plan.get('application_id')!=self.application.id:raise ValueError('Cross-application plan rejected')
  result=request(self.control_url+'/patch/apply',{k:plan[k] for k in ('edits','expected_sha','expected_hashes')}|{'token':os.environ.get('IC_CONTROL_TOKEN')},timeout=15)
  if result.get('error'):raise ValueError(result['error'])
  return result
 def rollback(self,inc):
  if inc.get('application_id')!=self.application.id:raise ValueError('Cross-application rollback rejected')
  r=request(self.control_url+'/patch/rollback',{'audit_id':inc['patch_audit_id'],'token':os.environ.get('IC_CONTROL_TOKEN')})
  if r.get('error'):raise ValueError(r['error'])
  return r
 def control(self,action):
  r=request(self.control_url+'/control',{'action':action},timeout=15)
  if r.get('error'):raise ValueError(r['error'])
  return r
 def sample(self,t):return {'error_rate':t['metrics']['error_rate'],'p95':t['metrics']['p95'],'pool':t['metrics'].get('pool',{}).get('utilization',0)}
 def present_metrics(self,t):return []
 def topology_health(self,t):return {}

def normalize_evidence(records,incident,application_id):
 if incident.get('application_id')!=application_id:raise ValueError('Incident belongs to another application')
 for record in records:
  if record.get('application_id',application_id)!=application_id or record.get('incident_id',incident['id'])!=incident['id']:raise ValueError('Cross-application evidence rejected')
  record.update(application_id=application_id,incident_id=incident['id'])
 return records

def build_plan(adapter,rca,t):
 proposal=({'action':'apply_ai_patch','edits':rca['hypothesis']['patch'],'title':'Review AI-generated repair','origin':'AI GENERATED','patch_source':'AI GENERATED'} if rca.get('ai_mode')=='LIVE AI' and rca.get('hypothesis',{}).get('patch') and not rca.get('requires_more_evidence') else adapter.propose(rca,t))
 if not proposal:return None
 proposal.setdefault('patch_source','DETERMINISTIC FALLBACK')
 proposal['origin']=proposal['patch_source']
 action=proposal['action']
 if action not in adapter.get_allowed_remediations():raise ValueError('Action not declared in application capabilities')
 edits=proposal['edits'];validation=adapter.validate_patch(edits)
 if validation.get('error'):return {'title':'Patch validation failed','validation':{'passed':False,'error':validation['error']}}
 risk='HIGH' if action=='apply_ai_patch' or len(edits)>1 or len(validation['diff'].splitlines())>45 else 'MEDIUM'
 return {**proposal,'id':uuid.uuid4().hex,'application_id':adapter.application.id,'validation':validation,'diff':validation['diff'],'risk':risk,'expected_sha':t['deployment']['sha'],'expected_hashes':t['local_source']['hashes'],'policy':'Human approval required. Only registered file capabilities may change. Exact application, plan, revision and content hashes must match. No shell or data deletion.','impact':'Restricted to '+adapter.application.name+': '+', '.join(e['path'] for e in edits),'rollback':'Restore audited original content only if no newer source edit exists. This can restore the fault.','verification':adapter.verification_description}
