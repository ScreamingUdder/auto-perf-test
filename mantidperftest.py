from mantid.simpleapi import  *
from kafka_test_utils.utils import jmxtool
import time
import pylab as pl
import mantid.api as api

class MantidKafkaPerfTest:
    """
    Runs a performance test of the Mantid kafka listener. This makes use of the jmxtool to query 
    the broker performance in terms of bytes in/bytes out per second of the events topic.
    """
    
    def __init__(self, InstrumentName, KafkaHost="sakura:9092", ZookeeperHost="sakura:9997", 
                OutputWorkspace="outws"):
        """
        :param KafkaHost: kafka server (listener) address (default sakura:9092).
        :param ZookeeperHost: zookeper server address (defaul sakura:9997).
        :param InstrumentName: Instrument name whose events topic will be monitored.
        :param OutputWorkspace: Container for Mantid to store events.
        """
        self.listenerHost = KafkaHost
        self.jmxhost = ZookeeperHost
        self.instrumentName = InstrumentName
        self._monitorLiveDataHandle = None
        self.jmxmonitor = None
        self.outputWs = OutputWorkspace
        
    def run(self):
        self._startLive()
        self._startKafkaMonitor()
        self._waitLive()
        self._plotKafkaMetrics()
        
    def _startLive(self):
        '''
        Start the live data algorithm 
        '''
        StartLiveData(FromNow=False, FromTime=False, FromStartOfRun=True, UpdateEvery=1.0, 
                    Instrument="ISIS_Kafka_Event", RunTransitionBehavior="Stop", OutputWorkspace=self.outputWs, 
                    Address=self.listenerHost, PreserveEvents=True, AccumulationMethod="Add", 
                    InstrumentName=self.instrumentName)
        
        #Grab most recent live data algorithm handle
        self._monitorLiveDataHandle = api.AlgorithmManagerImpl.Instance().newestInstanceOf("MonitorLiveData")
    
    def _startKafkaMonitor(self):
        self.jmxmonitor = jmxtool.JmxTool(host=self.jmxhost, topic=self.instrumentName+"_events")
        
    def _waitLive(self):
        while self._monitorLiveDataHandle.isRunning():
            time.sleep(1)    

    def _plotKafkaMetrics(self):
        results, plotFigure = self.jmxmonitor.get_output()
        print results;
        plotFigure.savefig("mantid_bytes_out_vs_time.svg")
        
if __name__ == "__main__":
    perftest = MantidKafkaPerfTest(InstrumentName="lm")
    perftest.run()
