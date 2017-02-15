import psutil
import time
import threading
import numpy as np
import matplotlib.pyplot as pl



class ResourceChecker:
    '''
    Collects CPU and Memory usage message on the system which runs this script.
    '''
    def __init__(self, UpdateTime=0.5):
        '''
        :param UpdateTime: How often resource statistics should be collected.
        '''
        self.update = UpdateTime;
        self.cpu = []
        self.memory = []
        self.keepRunning = None
        self.runThread = None
        
    def start(self):
        '''
        Non-blocking method which starts diagnostics in a new thread.
        '''
        self.runThread = threading.Thread(target=self._run)
        self.keepRunning = True
        self.runThread.start()
        
    def get_output(self):
        '''
        Kills diagnostic thread and gathers all information since start method
        was called.
        '''
        self.keepRunning = False
        
        if self.runThread is not None:
            self.runThread.join()
            self.runThread = None
            
        giga = 1024 * 1024 * 1024;
        usedmem = np.array(self.memory, dtype=float)
        usedmem /= giga
        
        totmem = float(psutil.virtual_memory().total)/giga
        time = np.arange(start=0, stop=usedmem.size*0.5, step=self.update, dtype=float)
        
        memPlotHandle = pl.figure()
        pl.ylabel("Memory Usage (GB)")
        pl.xlabel("Time (secs)")
        pl.title("System Memory Usage")
        pl.plot(time, usedmem)
        pl.ylim(0, totmem)
        
        cpuusage = np.array(self.cpu, dtype=float)
        cpuPlotHandle = pl.figure()
        pl.ylabel("CPU Usage (%)")
        pl.xlabel("Time (secs)")
        pl.title("System CPU Usage")
        pl.plot(time, cpuusage)
        pl.ylim(0, 100)
        
        return psutil.cpu_count(), totmem, memPlotHandle, cpuPlotHandle
        
    def _run(self):
        while self.keepRunning:
            self.cpu.append(psutil.cpu_percent(percpu=False))
            self.memory.append(float(psutil.virtual_memory().used))
            time.sleep(self.update)
            
            
if __name__ == "__main__":
    #Test ResourceCheck
    rc = ResourceChecker()
    rc.start()
    time.sleep(5)
    output = rc.get_output()
    print "cpu_cores="+str(output[0])+"%", "total memory="+str(output[1])+"GB"
    import pylab
    pylab.show()