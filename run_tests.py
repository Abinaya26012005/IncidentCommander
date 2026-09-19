"""Run integration checks and publish their actual results to the demo UI."""
import json, time, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Result(unittest.TextTestResult):
    records=[]
    def startTest(self,test):
        self.started=time.time();self.sub_started=self.started;super().startTest(test)
    def record(self,test,status):
        self.records.append({'name':getattr(test,'_testMethodName',str(test)),'status':status,'seconds':round(time.time()-getattr(self,'started',time.time()),2)})
    def addSubTest(self,test,subtest,err):
        super().addSubTest(test,subtest,err)
        if 'scenario' in subtest.params:
            self.records.append({'name':'scenario_'+subtest.params['scenario'],'status':'passed' if err is None else 'failed','seconds':round(time.time()-self.sub_started,2)})
            self.sub_started=time.time()
    def addSuccess(self,test): super().addSuccess(test);self.record(test,'passed')
    def addFailure(self,test,err): super().addFailure(test,err);self.record(test,'failed')
    def addError(self,test,err): super().addError(test,err);self.record(test,'error')
if __name__=='__main__':
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    (ROOT/'test-results.json').write_text(json.dumps({'timestamp':time.time(),'test_methods':result.testsRun,'tests':result.records,'passed':result.wasSuccessful(),'scope':f'{result.testsRun} test methods plus scenario breakdowns: both applications over real HTTP, isolation, restricted patch checks, UI state tests, and a mocked AI adapter. Temporary SQLite/Git data and isolated ports. External AI/audio providers are not live-tested.'},indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
