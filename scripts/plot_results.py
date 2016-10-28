# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2016, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

"""Plot results for a specific detector."""

import argparse
import csv
import datetime
import json
import math
import os

from nupic.algorithms import anomaly_likelihood

from plotly import tools
import plotly.offline as py
from plotly.graph_objs import Bar, Marker, Scatter



def parseResults(resultsPath):
  ts = []
  values = []
  anomalyScores = []
  rawScores = []
  labels = []
  with open(resultsPath) as f:
    reader = csv.reader(f)
    headers = reader.next()
    tsIdx = headers.index("timestamp")
    valueIdx = headers.index("value")
    asIdx = headers.index("anomaly_score")
    rsIdx = headers.index("raw_score")
    labelIdx = headers.index("label")
    for row in reader:
      ts.append(datetime.datetime.strptime(row[tsIdx], "%Y-%m-%d %H:%M:%S"))
      values.append(float(row[valueIdx]))
      anomalyScores.append(float(row[asIdx]))
      rawScores.append(float(row[rsIdx]))
      labels.append(int(row[labelIdx]))
  return ts, values, anomalyScores, rawScores, labels



def plotResults(ts, values, anomalyScores, rawScores, labels, threshold):
  data1 = []
  data1.extend(getValuesPlot(ts, values))
  data1.extend(getWindowsPlot(ts, labels, values))
  data2 = []
  data2.extend(getAnomalyScorePlot(ts, anomalyScores))
  data3 = []
  #data3.extend(getAnomalyScorePlot(ts, computeAnomalyScores(ts, rawScores, values)))
  data3.extend(getAnomalyScorePlot(ts, rawScores))
  fig = tools.make_subplots(rows=3, cols=1)
  for trace in data1:
    fig.append_trace(trace, 1, 1)
  for trace in data2:
    fig.append_trace(trace, 2, 1)
  for trace in data3:
    fig.append_trace(trace, 3, 1)
  #print "-------------------------"
  #print fig
  #print dir(fig)
  #print "-------------------------"
  #import sys; sys.exit()
  py.plot(fig)



def getValuesPlot(ts, values):
  return [Scatter(x=ts, y=values)]



def getWindowsPlot(ts, labels, values):
  maxVal = max(values)
  windowsValues = [maxVal*label for label in labels]
  return [Bar(x=ts, y=windowsValues, name="Anomaly Windows",
              marker=Marker(color="rgb(220, 100, 100)"), opacity=0.3)]



def getAnomalyScorePlot(ts, anomalyScores):
  return [Bar(x=ts, y=anomalyScores)]



def computeAnomalyScores(ts, rawScores, values):
  probationPercent = 0.15
  probationPeriod = getProbationPeriod(probationPercent, len(rawScores))
  numentaLearningPeriod = math.floor(probationPeriod / 2.0)
  likelihood = anomaly_likelihood.AnomalyLikelihood(
    claLearningPeriod=numentaLearningPeriod,
    estimationSamples=probationPeriod-numentaLearningPeriod,
    reestimationPeriod=100
  )

  anomalyScores = []
  minVal = None
  maxVal = None
  for rawScore, value, dt in zip(rawScores, values, ts):
    forceAnomaly = False
    if minVal != maxVal:
      if value > (((maxVal-minVal) * 0.2) + maxVal):
        forceAnomaly = True
    #rawScore = rawScore ** 0.5
    anomalyScore = likelihood.anomalyProbability(value, rawScore, dt)
    logScore = likelihood.computeLogLikelihood(anomalyScore)
    if forceAnomaly:
      logScore = 1.0
    anomalyScores.append(logScore)

    if minVal is None or value < minVal:
      minVal = value
    if maxVal is None or value > maxVal:
      maxVal = value
  return anomalyScores



def getProbationPeriod(probationPercent, fileLength):
  """Return the probationary period index."""
  return min(
    math.floor(probationPercent * fileLength),
    probationPercent * 5000)



#def getDetectionsPlot(ts, anomalyScores, labels, threshold):
#  fp = []
#  tp = []
#  for dt, anomalyScores, label in zip(ts, anomalyScores, labels):
#    if anomalyScore >= threshold:
#      if label == 1:
#        tp.append(dt)
#      else:
#        fp.append(dt)
#
#  fpPlot = Scatter(x=fp,
#                   y=FP["value"],
#                      mode="markers",
#                      name=name,
#                      text=["anomalous data"],
#                      marker=Marker(
#                        color="rgb(200, 20, 20)",
#                        size=15.0,
#                        symbol=symbol,
#                        line=Line(
#                          color="rgb(200, 20, 20)",
#                          width=2
#                        )
#                      ))
#    # TPs:
#    tpTrace = Scatter(x=[tp[1]["timestamp"] for tp in TP],
#                      y=[tp[1]["value"] for tp in TP],
#                      mode="markers",
#                      name=name,
#                      text=["anomalous data"],
#                      marker=Marker(
#                        color="rgb(20, 200, 20)",
#                        size=15.0,
#                        symbol=symbol,
#                        line=Line(
#                          color="rgb(20, 200, 20)",
#                          width=2
#                        )
#                      ))



def getThreshold(detector, profile):
  with open(os.path.join(os.getcwd(), os.path.dirname(__file__), os.pardir, "config", "thresholds.json")) as f:
    thresholdsData = json.load(f)
    return thresholdsData[detector][profile]["threshold"]



def _parseArgs():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--detector", required=True)
  parser.add_argument("--profile", required=True)
  parser.add_argument("--relPath", required=True)
  args = parser.parse_args()
  return args.detector, args.profile, args.relPath



def main():
  py.init_notebook_mode()
  detector, profile, relPath = _parseArgs()
  relPath = relPath.replace("/", "/{}_".format(detector))
  resultsPath = os.path.join(os.getcwd(), os.path.dirname(__file__), os.pardir, "results", detector, relPath)
  threshold = getThreshold(detector, profile)
  ts, values, anomalyScores, rawScores, labels = parseResults(resultsPath)
  plotResults(ts, values, anomalyScores, rawScores, labels, threshold)



if __name__ == "__main__":
  main()
