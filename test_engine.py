import unittest
import pandas as pd
from engine import compare,aggregate,km
class TestEngine(unittest.TestCase):
 def test_km(self):self.assertEqual(km('10+450'),10450)
 def test_colors(self):
  p=pd.DataFrame([{'progressiva_m':10000,'h_mm':50,'rotaia_alzata':'sx','verificato':True},{'progressiva_m':10020,'h_mm':50,'rotaia_alzata':'sx','verificato':True}])
  m=pd.DataFrame([{'progressiva_m':10000,'rilevato_mm':60,'verificato':True},{'progressiva_m':10005,'rilevato_mm':61,'verificato':True},{'progressiva_m':10010,'rilevato_mm':170,'verificato':True},{'progressiva_m':10015,'rilevato_mm':0,'verificato':False}])
  d=compare(p,m)
  self.assertEqual(d.codice.tolist(),['VERDE','GIALLO','ROSSO','NON LEGGIBILE'])
 def test_aggregation(self):
  d=pd.DataFrame({'progressiva_m':[10000,10005,10010,10015],'codice':['VERDE','VERDE','GIALLO','VERDE'],'scostamento_mm':[0,1,11,0]})
  a=aggregate(d);self.assertEqual(len(a),3);self.assertEqual(a.iloc[0].punti,2)
 def test_sign(self):
  p=pd.DataFrame([{'progressiva_m':10000,'h_mm':50,'rotaia_alzata':'dx','verificato':True}]);m=pd.DataFrame([{'progressiva_m':10000,'rilevato_mm':-50,'verificato':True}]);self.assertEqual(compare(p,m).iloc[0].codice,'VERDE')
if __name__=='__main__':unittest.main()
