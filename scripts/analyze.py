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

"""TODO"""

import argparse
import collections
import csv
import datetime
import json
import os

from nab.corpus import Corpus

DESCRIPTION = "Utility for analyzing NAB results."
RESULTS_DIR = os.path.join(os.getcwd(), os.path.dirname(__file__),
                           os.path.pardir, "results")
WINDOWS_PATH = os.path.join(os.getcwd(), os.path.dirname(__file__),
                            os.path.pardir, "labels", "combined_windows.json")
THRESHOLDS_PATH = os.path.join(os.getcwd(), os.path.dirname(__file__),
                               os.path.pardir, "config", "thresholds.json")
PROFILES_PATH = os.path.join(os.getcwd(), os.path.dirname(__file__),
                             os.path.pardir, "config", "profiles.json")



def analyze(detector, profile):
  windows = getWindows()
  threshold, score = _getThreshold(detector, profile)
  weights = _getWeights(profile)
  falsePositives = collections.defaultdict(list)
  detectorResultsPath = os.path.abspath(os.path.join(RESULTS_DIR, detector))
  for relDir in os.listdir(detectorResultsPath):
    fullPath = os.path.join(detectorResultsPath, relDir)
    if os.path.isdir(fullPath):
      for result in os.listdir(fullPath):
        with open(os.path.join(fullPath, result)) as resultFile:
          relPath = os.path.join(relDir, result.partition("_")[2])
          relWindows = windows[relPath]
          reader = csv.reader(resultFile)
          header = reader.next()
          for row in reader:
            row = dict(zip(header, row))
            label = bool(int(row["label"]))
            dt = _dt(row["timestamp"])
            inWindow = _inWindow(dt, relWindows)
            if label:
              assert inWindow is not None
            else:
              assert inWindow is None
            score = float(row["anomaly_score"])
            detection = score >= threshold
            if detection:
              if inWindow is not None:
                inWindow[1].append(dt)
              else:
                falsePositives[relPath].append(dt)

  tp = 0
  detectedWindows = 0
  undetectedWindows = 0
  sortedWindows = []
  for path, data in windows.iteritems():
    sortedWindows.append([0, path])
    for _bounds, detections in data:
      tp += len(detections)
      if len(detections) > 0:
        detectedWindows += 1
      else:
        undetectedWindows += 1
        sortedWindows[-1][0] += 1
  print "total true positives", tp
  print "detected windows", detectedWindows
  print "max positive from detected windows", float(detectedWindows) * weights["tpWeight"]
  print "undetected windows", undetectedWindows
  print "max positive from undetected windows", (float(undetectedWindows) * weights["tpWeight"]) + (float(undetectedWindows) * weights["fnWeight"])

  fp = 0
  for _path, detections in falsePositives.iteritems():
    fp += len(detections)
  print "false positives", fp
  print "max negative from fp", float(fp) * weights["fpWeight"]

  # Find files with most missed windows
  sortedWindows.sort()
  for undetectedWindows, path in sortedWindows:
    if undetectedWindows > 0:
      print path
      #print "{}: {}".format(undetectedWindows, path)



def getWindows():
  with open(WINDOWS_PATH) as f:
    windowsData = json.load(f)

  windows = {}
  for relPath, relWindows in windowsData.iteritems():
    windows[relPath] = []
    for w in relWindows:
      parsedWindow = (_dt(w[0]), _dt(w[1]))
      windows[relPath].append((parsedWindow, []))
  return windows



def _getThreshold(detector, profile):
  with open(THRESHOLDS_PATH) as f:
    thresholds = json.load(f)
  tmp = thresholds[detector][profile]
  return tmp["threshold"], tmp["score"]



def _getWeights(profile):
  with open(PROFILES_PATH) as f:
    profiles = json.load(f)
  return profiles[profile]["CostMatrix"]



def _inWindow(dt, windows):
  for w in windows:
    if dt >= w[0][0] and dt <= w[0][1]:
      return w
  return None



def _dt(s):
  s = s.split(".")[0]
  return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")



def main():
  parser = argparse.ArgumentParser(description=DESCRIPTION)
  parser.add_argument("--detector", required=True)
  parser.add_argument("--profile", default="standard")
  args = parser.parse_args()
  analyze(args.detector, args.profile)



if __name__ == "__main__":
  main()
