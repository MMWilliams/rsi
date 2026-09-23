"""Run the same opened sensor-edit diagnostic on the earlier 24-bank panel."""
from rsi.common import ROOT
import listwise_sensor_edit_diagnostic as diagnostic

diagnostic.SOURCE=ROOT/'runs/task-listwise-top200-transfer-20260918'
diagnostic.OUT=ROOT/'analysis/listwise-sensor-edit-source-20260918.json'

if __name__=='__main__':diagnostic.main()
