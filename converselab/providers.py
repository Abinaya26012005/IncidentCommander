"""Local provider contracts. These deterministic providers never claim external AI/audio."""
from abc import ABC, abstractmethod

DOCUMENTS=[
 {'id':'KB-001','title':'Billing dates','terms':['payment','bill','due','credit','card'],'text':'Your example account payment is due on September 25. This is seeded demo account information.'},
 {'id':'KB-002','title':'Order tracking','terms':['order','delivery','package','tracking'],'text':'Your example order is in transit and is expected within 2 business days. Track it from Orders in your account.'},
 {'id':'KB-003','title':'Returns and refunds','terms':['return','refund','cancel'],'text':'You can request a return within 30 days of delivery. Approved refunds take 5–7 business days.'},
 {'id':'KB-004','title':'Account support','terms':['password','account','support','help'],'text':'Use the password reset link for account access. For other issues, contact the support team with your case reference.'}
]

class STTProvider(ABC):
 @abstractmethod
 def transcribe(self,text):pass
class LLMProvider(ABC):
 @abstractmethod
 def generate(self,question,documents,version):pass
class TTSProvider(ABC):
 @abstractmethod
 def synthesize(self,text):pass
class DemoSTTProvider(STTProvider):
 def transcribe(self,text):return {'transcript':text,'provider':'DemoSTTProvider','simulated':True}
class DemoLLMProvider(LLMProvider):
 def generate(self,question,documents,version):
  return {'answer':documents[0]['text'] if documents and version=='v1' else '', 'citations':[d['id'] for d in documents], 'provider':'DemoLLMProvider','simulated':True}
class DemoTTSProvider(TTSProvider):
 def synthesize(self,text):return {'delivered':True,'transcript':text,'audio_available':False,'provider':'DemoTTSProvider','simulated':True}
def retrieve(question):
 scores=[(sum(term in question.lower() for term in d['terms']),d) for d in DOCUMENTS]
 best=max(scores,key=lambda x:x[0]);return [best[1]] if best[0] else [DOCUMENTS[-1]]
