import psutil
import time
import threading
import numpy as np
import matplotlib.pyplot as pl


class ResourceChecker:
    """
    Collects CPU and Memory usage message on the system which runs this script.
    """

    def __init__(self, update_time=0.5):
        """
        :param update_time: How often resource statistics should be collected.
        """
        self.update = update_time
        self.cpu = []
        self.memory = []
        self.keep_running = None
        self.run_thread = None

    def start(self):
        """
        Non-blocking method which starts diagnostics in a new thread.
        """
        self.run_thread = threading.Thread(target=self._run)
        self.keep_running = True
        self.run_thread.start()

    def get_output(self):
        """
        Kills diagnostic thread and gathers all information since start method
        was called.
        """
        self.keep_running = False

        if self.run_thread is not None:
            self.run_thread.join()
            self.run_thread = None

        giga = 1024 * 1024 * 1024
        used_mem = np.array(self.memory, dtype=float)
        used_mem /= giga

        totmem = float(psutil.virtual_memory().total) / giga
        time = np.arange(start=0, stop=used_mem.size * 0.5, step=self.update, dtype=float)

        mem_plot_handle = pl.figure()
        pl.ylabel("Memory Usage (GB)")
        pl.xlabel("Time (secs)")
        pl.title("System Memory Usage")
        pl.plot(time, used_mem)
        pl.ylim(0, totmem)

        cpu_usage = np.array(self.cpu, dtype=float)
        cpu_plot_handle = pl.figure()
        pl.ylabel("CPU Usage (%)")
        pl.xlabel("Time (secs)")
        pl.title("System CPU Usage")
        pl.plot(time, cpu_usage)
        pl.ylim(0, 100)

        return psutil.cpu_count(), totmem, mem_plot_handle, cpu_plot_handle

    def _run(self):
        while self.keep_running:
            self.cpu.append(psutil.cpu_percent(percpu=False))
            self.memory.append(float(psutil.virtual_memory().used))
            time.sleep(self.update)


if __name__ == "__main__":
    # Test ResourceCheck
    rc = ResourceChecker()
    rc.start()
    time.sleep(5)
    output = rc.get_output()
    print "cpu_cores=" + str(output[0]) + "%", "total memory=" + str(output[1]) + "GB"
    import pylab

    pylab.show()
