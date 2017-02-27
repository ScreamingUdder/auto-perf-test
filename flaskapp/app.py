from flask import Flask, render_template
import matplotlib.pyplot as plt
import matplotlib.dates as dates
import datetime
import numpy as np
import mpld3
import os

app = Flask(__name__)


@app.route("/")
@app.route('/index')
def main():
    # print os.getcwd()
    data = np.genfromtxt('flaskapp/duration_log.txt', delimiter=',', names=['timestamps', 'duration', 'sha'],
                         dtype=('|S19', float, '|S40'))
    if data['timestamps'].size < 2:
        return render_template('index.html', plot='Insufficient data points to plot')

    fig, ax = plt.subplots(subplot_kw=dict(axisbg='#EEEEEE'))
    datetimes = [datetime.datetime.strptime(timestamp.translate(None, ':-'), "%Y%m%dT%H%M%S") for timestamp in
                 data['timestamps']]

    xfmt = dates.DateFormatter('%H:%M:%S:%f')
    ax.xaxis.set_major_formatter(xfmt)
    time_plot = ax.plot(datetimes, data['duration'])
    ax.grid(color='white', linestyle='solid')

    ax.set_title("MonitorLiveData duration - Performance test log", size=16)

    tooltip = mpld3.plugins.PointLabelTooltip(time_plot, labels=data['sha'].tolist())
    mpld3.plugins.connect(fig, tooltip)
    duration_plot = mpld3.fig_to_html(fig, template_type="simple")

    return render_template('index.html', plot=duration_plot)


if __name__ == "__main__":
    app.run(debug=False)
