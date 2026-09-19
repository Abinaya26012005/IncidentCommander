import json
DEFAULT={'knowledge_available':True,'tts_available':True,'llm_available':True,'stt_latency_ms':120,'knowledge_latency_ms':70,'llm_latency_ms':160,'tts_latency_ms':100,'prompt_version':'v1'}
def validate(content):
 value=json.loads(content)
 if not isinstance(value,dict) or set(value)!=set(DEFAULT):raise ValueError('Only the documented ConverseLab configuration keys are allowed')
 for key,default in DEFAULT.items():
  if type(value[key]) is not type(default):raise ValueError('Invalid configuration type: '+key)
  if key.endswith('_ms') and not 0<=value[key]<=10000:raise ValueError('Latency outside sandbox bounds')
 if value['prompt_version'] not in ('v1','v2-broken'):raise ValueError('Unsupported sandbox prompt version')
 return value
