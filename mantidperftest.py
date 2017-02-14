from mantid.simpleapi import *
from kafka_test_utils.utils import jmxtool
import time
import pylab as pl
import mantid.api as api


class MantidKafkaPerfTest:
    """
    Runs a performance test of the Mantid kafka listener. This makes use of the jmxtool to query 
    the broker performance in terms of bytes in/bytes out per second of the events topic.
    """

    def __init__(self, instrument_name, kafka_host="sakura:9092", zookeeper_host="sakura:9997",
                 output_workspace="outws"):
        """
        :param kafka_host: kafka server (listener) address (default sakura:9092).
        :param zookeeper_host: zookeeper server address (default sakura:9997).
        :param instrument_name: Instrument name whose events topic will be monitored.
        :param output_workspace: Container for Mantid to store events.
        """
        self.listenerHost = kafka_host
        self.jmxhost = zookeeper_host
        self.instrumentName = instrument_name
        self._monitorLiveDataHandle = None
        self.jmxmonitor = None
        self.outputWs = output_workspace

    def run(self):
        self._start_kafka_monitor()
        self._start_live()
        self._wait_live()
        self._plot_kafka_metrics()

    def _start_live(self):
        """
        Start the live data algorithm 
        """
        StartLiveData(FromNow=False, FromTime=False, FromStartOfRun=True, UpdateEvery=1.0,
                      Instrument="ISIS_Kafka_Event", RunTransitionBehavior="Stop", OutputWorkspace=self.outputWs,
                      Address=self.listenerHost, PreserveEvents=True, AccumulationMethod="Add",
                      InstrumentName=self.instrumentName)

        # Grab most recent live data algorithm handle
        self._monitorLiveDataHandle = api.AlgorithmManagerImpl.Instance().newestInstanceOf("MonitorLiveData")

    def _start_kafka_monitor(self):
        self.jmxmonitor = jmxtool.JmxTool(host=self.jmxhost, topic=self.instrumentName + "_events",
                                          interval_milliseconds=500)

    def _wait_live(self):
        while self._monitorLiveDataHandle.isRunning():
            time.sleep(1)

    def _plot_kafka_metrics(self):
        results, plot_figure = self.jmxmonitor.get_output()
        print results
        plot_figure.savefig("mantid_bytes_out_vs_time.svg")


if __name__ == "__main__":
    perftest = MantidKafkaPerfTest(instrument_name="lm")
    perftest.run()
