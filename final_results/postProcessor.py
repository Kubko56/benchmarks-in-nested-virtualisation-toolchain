#!/usr/bin/python

# simple charting app which visualise post-process results. Thus answering the final question.
# chart functions copypasted from result_processing.py. Would be nice to have shared library
# most of the inputs are hardcoded
# processed files are generated by generate_all.sh and the keys are generated by result_processing.py
# long story short, it operates over content of _pregenerated_reports: inverted_results/*properties.sort.uniq  and passrates.properties.sort.uniq

import os
import sys
import re
from functools import cmp_to_key
import matplotlib.pyplot as plt 

def is_html():
    #if not defined then true, it no longer have sense without it
    return (os.environ.get('HTML') is  None or os.environ.get('HTML') == "true")

def is_avg():
    # geom by default as it is more real
    return os.environ.get('POST_AVG') is not None and os.environ.get('POST_AVG') == "true"

# scenario 1: gathered absolute values from inverted_results/*properties.sort.uniq  
# min, max, avg, med
# thus we can show impact of virtualisation on performance

# scenario 2: gathered  vlaues from passrates.properties.sort.uniq (note there is trailing %:-/
# there we can show which jdk was most/less stable under which virtualisation
# there we can show, which virtualisation generally improveds stability, and which degraded it

# scenario 3: the final answer from inverted_results/*properties.sort.uniq
# here we have relative stability results per jdk and per virtualisation
# there is hidden final answer of imapct of (nested) virtualisation to accuracy
# ideally also add avgs from various combinations
# as it is possible to really iterate thi as the pasrates, its the way to go
#  however, it would be ok to pas each to different file/dir due of size

 

# object to keep values of passrates.properties.sort.uniq
class xJxBxV(object):
    jdkFromDir = ""
    benchmarkFromDir = ""
    virtualizationFromDir = "" # dont use!
    originalDir = ""
    originalKey = ""
    value = 0
    virtualizationFromKey=""
    benchmarkFromKey=""

    
    # the file always contains  virtualisation_benchmark=value% (the percentage must be filtered out)
    # and is in directory, which says, which jdks and which benchmarks and which virtualisations were used
    # so we need the parent dir name, and the value read from it
    def __init__(self, dirName, keyName, value, skip=False):
        self.value = parse_number(re.sub("%","",value))
        self.originalDir = dirName
        self.originalKey = keyName
        #eprint(str(self.value) + " " + self.originalDir + " " + self.originalKey)
        # now parse origDir and Key. The final benchmark and virtualisation should match
        # if not, use one (and with other objects) use it consitently.
        # Benchmark name may contain several _ :(
        self.jdkFromDir = dirName.split("_")[0];  # eg jdk11, all, allJ
        self.jdkFromDir = sanitizeAll(self.jdkFromDir)
        initOrAdd(allJdks, self.jdkFromDir, skip);
        self.benchmarkFromDir = dirName.split("_")[1]; 
        self.benchmarkFromDir = sanitizeAll(self.benchmarkFromDir) # this one contains name of benchmark or ALL. Thats why we ar eusing the second everywhere. That may chnage
        initOrAdd(allBenchmarks, self.benchmarkFromDir, skip)
        # NO! this virt is not used in JVbkmr; dont use
        self.virtualizationFromDir = re.sub(self.jdkFromDir+"_"+self.benchmarkFromDir+"_", "", dirName) #container_results  containers_in_container_results
        self.benchmarkFromKey = self.originalKey.split("_")[-1];
        self.benchmarkFromKey = sanitizeAll(self.benchmarkFromKey)
        initOrAdd(allBenchmarks, self.benchmarkFromKey, skip)
        #YES, this  is shared with JVbkmr; use this
        self.virtualizationFromKey = re.sub("_"+self.benchmarkFromKey, "", self.originalKey)  #container-results  containers_in_container
        self.virtualizationFromKey = sanitizeAll(self.virtualizationFromKey)
        initOrAdd(allVirtualisations, self.virtualizationFromKey, skip)
        #eprint(niceString(self))

    def niceString(self):
        return str(self.value) + " (" + self.jdkFromDir+ " " + self.benchmarkFromDir+" " + self.virtualizationFromDir + ") (" + self.virtualizationFromKey + " " +self.benchmarkFromKey+")"

    def equalsKey(self):
        return self.jdkFromDir+ " " + " " + self.virtualizationFromKey + " " +self.benchmarkFromKey

# object to keep values of inverted_results/*properties.sort.uniq
# name contains jdks in measurment
# inside is very complicated key virtualisation_benchmark:key:metric:resultTyp=value
# there is no percentage for relative metrics, but should be. Count with that. will be added
class JVbkmr(object):
    jdkFromName = ""
    originalKey = ""
    value = 0
    isRelative=False # based on the future % char
    virtualisation=""
    benchmark=""
    key=""
    metric=""
    resultType=""

    def __init__(self, fileName, keyName, value, skip=False):
        self.value = parse_number(re.sub("%","",value))
        self.jdkFromName = re.sub("\\.properties.*","",fileName)
        self.jdkFromName = sanitizeAll(self.jdkFromName)
        initOrAdd(allJdks, self.jdkFromName, skip); # eg java-11
        self.originalKey = keyName
        #eprint(str(self.value) + " " + self.jdkFromName + " " + self.originalKey)
        # now parse originalKey
        splited = self.originalKey.split(":");
        self.resultType=splited[3]
        if not skip:
            allTypes.add(self.resultType)
        self.metric=splited[2]
        if not skip:
            allMetrics.add(self.metric)
        self.key=splited[1]
        if (self.key.find("Time")>=0):
            self.value=-1*self.value
        if (self.resultType.find("-")>=0):
            self.value=abs(self.value)
        virtAndbench=splited[0]
        self.benchmark = virtAndbench.split("_")[-1];
        self.benchmark = sanitizeAll(self.benchmark)
        initOrAdd(allBenchmarks, self.benchmark, skip)
        if not skip:
            if (self.benchmark in allKeysPerBenchmark):
                allKeysPerBenchmark[self.benchmark].add(self.key)
            else:
                allKeysPerBenchmark[self.benchmark]={self.key}
        self.virtualisation = re.sub("_"+self.benchmark, "", virtAndbench)  #container-results  containers_in_container
        self.virtualisation = sanitizeAll(self.virtualisation)
        initOrAdd(allVirtualisations, self.virtualisation, skip)
        #eprint(niceString(self))
    
    def niceString(self):
        return str(self.value) +" " + self.jdkFromName + " (" + self.virtualisation+ " " + self.benchmark+" " + self.key + " " + self.metric + " " +self.resultType+")"

def initOrAdd(hashmap, key, skip):
        if skip: return
        if (key in hashmap):
            hashmap[key]+=1
        else:
            hashmap[key]=1

def sanitizeAll(where):
    # this function sanitize small differences in various names. It may appear that they do not belong together. we will see
    q = re.sub(".*all.*","all",where)
    q = re.sub("jdk8.*","java-1.8.0",q)
    q = re.sub("jdk","java-",q)
    #q = re.sub("java-$","all-javas",q)# currenlty all x all-javas may mean something different. will be investigated
    q = re.sub("java-$","all",q)
    return q;

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def parse_number(line):
    #print("parsing number: ", line)  
    parsed_number = ""
    for char in line:
        if (char == '.'):
            parsed_number += '.'
        if not (char.isdigit() or char == '.'):
            parsed_number = ""
        elif (char.isdigit()):
            parsed_number += char
    #print("parsed number: ", parsed_number)  
    if parsed_number == "":
        return 0
    #print("rounded number: ", round(float(parsed_number)))
    return float(parsed_number)

def selectFinals(jdkFromName, key, virtualisation, benchmark, metric, resultType, finals):
    subset=[];
    for final in finals:
        if ((jdkFromName is None or jdkFromName == final.jdkFromName)
        and (key is None or key == final.key)
        and (virtualisation is None or virtualisation == final.virtualisation)
        and (benchmark is None or benchmark == final.benchmark)
        and (metric is None or metric == final.metric)
        and (resultType is None or resultType == final.resultType)
        ):
            subset.append(final);
    return subset

def selectCrashrate(jdkFromDir, virtualizationFromKey, benchmarkFromKey):
    subset=[];
    for final in passrates:
        if ((jdkFromDir is None or jdkFromDir == final.jdkFromDir)
        and (virtualizationFromKey is None or virtualizationFromKey == final.virtualizationFromKey)
        and (benchmarkFromKey is None or benchmarkFromKey == final.benchmarkFromKey)
        ):
            subset.append(final);
    return subset


def create_figure(x1, y1, x_name, y_name, name, clear_plot, figg = None):
    eprint("creating figure. x:", y1, ", y:", x1)
    #print("values:", y1)

    # enabling labels rotations
    if (figg is None):
        fig = plt.figure(figsize=(max(len(x1)/5+1,10),5))
    else:
        fig = figg
    ax = plt.gca()
    # plotting the points  
    ax.plot(x1, y1) 
    
    # naming the x axis 
    plt.xlabel(x_name) 
    # naming the y axis 
    plt.ylabel(y_name) 
    
    # giving a title to my graph 
    plt.title(name) 
    
    # rotate x axe labels by vertically and making room for them
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    fig.subplots_adjust(top=0.9)
    fig.subplots_adjust(bottom=0.3)
    fig.tight_layout()

    # function to plot the plot 
    if (clear_plot):
        name_fig = name + ".png"
        plt.savefig(name_fig)
        file_path = os.getcwd() + "/" + name_fig
        if is_html():
            print("<br/><a href='"+name_fig+"'><img src='"+name_fig+"'></img></a><br/>")
        else:
            print("file: ", file_path.strip())
    if (clear_plot):
        plt.clf()
    return fig

def readPassRates(root, filename, name):
    file = open(filename).readlines()
    for line in file:
        value = line.split("=")[1].strip()
        key = line.split("=")[0].strip()
        passrates.append(xJxBxV(os.path.basename(root), key, value))

def readFinals(root, filename, name):
    file = open(filename).readlines()
    for line in file:
        value = line.split("=")[-1].strip()
        key = re.sub("="+value+"\n", "", line); # there can be = in key:(
        finals.append(JVbkmr(name, key, value))

def metricToString(m):
    if (m=="m1"):
        return "all runs of one jdk are treated as INDIVIDUAL items"
    if (m=="m2a"):
        return "all runs of one jdk were made AVARAGE before processing"
    if(m=="m2m"):
        return "all runs of one jdk were made MEDIAN before processing"
    return "unknown metric: " + m;

def tableOfContext13(avgs):
    olo()
    for jdk in allJdks:
        lio();ahref(jdk, jdk);lie()
        olo()
        for benchmark in allBenchmarks:
            if (benchmark == "all"):
                continue
            lio();ahref(benchmark, jdk+"_"+benchmark);lie()
            olo()
            for metric in allMetrics:
                lio();ahref(metric, jdk+"_"+benchmark+"_"+metric);lie();
                olo()
                for key in allKeysPerBenchmark[benchmark]:
                    iddqd=jdk + "_" + benchmark + "_" + metric+"_"+key
                    lio();ahref(key, iddqd);lie()
                if avgs:
                    iddqd=jdk + "_" + benchmark + "_" + metric+"_avg"
                    lio();ahref("avg", iddqd);lie()
                ole()
            if avgs:
                iddqd=jdk + "_" + benchmark + "_avg_avg"
                lio();ahref("avg", iddqd);lie()
            ole()
        if avgs:
            iddqd=jdk + "_avg_avg_avg"
            lio();ahref("avg", iddqd);lie()            
        ole()
    ole()
    olo()        
    if avgs:
        iddqd="avgX_avg_avg_avg"
        lio();ahref("avg of all (with all, thus wrong)", iddqd);lie() 
        iddqd="avg_avg_avg_avg"
        lio();ahref("avg of all", iddqd);lie() 
    ole()
    tag("hr","");

def tableOfContext2(allJdks, allBenchmarks, selectionHelper):
    olo()
    for jdk in allJdks:
        lio();ahref(jdk, jdk+"-"+selectionHelper);lie()
        olo()
        for benchmark in allBenchmarks:
            lio();ahref(benchmark, jdk+"_"+benchmark+"-"+selectionHelper);lie()
        ole()
    ole()
    tag("hr","");

def tago(t, idd = None):
    if (is_html()):
        if (idd is None):
            print("<"+t+">")
        else:
            print("<"+t+" id='"+idd+"'>")
def tage(t):
    if (is_html()):
        print("</"+t+">")

def tag(t,s,idd = None):
    tago(t,idd)
    print(s)
    tage(t)

def h(i,s,idd = None):
    tag("h"+str(i),s, idd)

def h1(s,idd = None):
    h(1,s,idd)

def h2(s,idd = None):
    h(2,s,idd)

def h3(s,idd = None):
    h(3,s, idd)

def h4(s,idd = None):
    h(4,s, idd)

def h5(s,idd = None):
    h(5,s, idd)

def pre(s,idd = None):
    tag("pre",s, idd)


def ahref(s,href):
    if (is_html()):
        print("<a href='#"+href+"'>")
    print(s)
    if (is_html()):
        print("</a>")

def olo():
    tago("ol")

def ole():
    tage("ol")

def lio():
    tago("li")

def lie():
    tage("li")

def keyToStr(key):
    if key is None:
        return "all";
    return key

def getChartHeight(allTypes, interestedTypes, jdk, key, virt, benchmark, metric, finals):
    #calculsting height of chart, to adjust shift properly
    maxi=1
    mini=10000000000000
    for x in interestedTypes:
        if x in allTypes:
            subset = selectFinals(jdk, key, virt, benchmark, metric, x, finals)
            # if to sort, then by virtualization name
            subset = sorted(subset,  key=lambda r: r.virtualisation)
            for item in subset:
                maxi=max(maxi, item.value)
                mini=min(mini, item.value)
    chartHeight=maxi-mini
    return chartHeight

def drawChartForInterestedTypes(shift, allTypes, interestedTypes, jdk, key, virt, benchmark, metric, preffix, decorator, legend, iddqd, avgsOfAllKeys, finals):
    if (is_html()): 
        print("<pre>")  
    chartHeight = getChartHeight(allTypes, interestedTypes, jdk, key, virt, benchmark, metric, finals)
    fig_transfer = None
    i=-1
    for x in interestedTypes:
        i+=1
        if x in allTypes:  
            subset = selectFinals(jdk, key, virt, benchmark, metric, x, finals)
            # if to sort, then by virtualization name
            subset = sorted(subset,  key=lambda r: r.virtualisation)
            c=-1
            for item in subset:
                c+=1
                if is_avg():
                    avgsOfAllKeys[x][c]=avgsOfAllKeys[x][c]+item.value
                else:
                    avgsOfAllKeys[x][c]=avgsOfAllKeys[x][c]*item.value
            xAxe = list(map(lambda final: final.virtualisation, subset))
            # shift 0.05 was ok for 10, but to big for 1
            relshift=0
            if shift:
                relshift=i*(chartHeight/150.0)
                relshift=min(1,relshift)#?
                relshift=max(0.0001,relshift)#?
            yAxe = list(map(lambda final: final.value+relshift, subset))
            for item in subset:
                print(x+ " " + str(item.value)+" "+item.virtualisation )
            if (not (i == len(interestedTypes)-1)):
                fig_transfer = create_figure(xAxe, yAxe, "rewritten", key+decorator, preffix+iddqd, False, fig_transfer)
            else:
                create_figure(xAxe, yAxe, legend, key+decorator, preffix+iddqd, True, fig_transfer)
                if (is_html()):
                    print("</pre>")
        else:
            pre("missing value: " + x)   

def avgAndAdd(toBeAvg, listToCountCountFrom, toBeAddedTo1, toBeAddedTo2, interestedTypes, allVirtualisations):
    for x in interestedTypes:
        cc=-1
        for v in allVirtualisations:
            cc+=1
            if is_avg():
                toBeAvg[x][cc] = toBeAvg[x][cc] / float(str(len(listToCountCountFrom)))
            else:
                toBeAvg[x][cc] = abs(toBeAvg[x][cc]) ** (float("1.0")/float(str(len(listToCountCountFrom))))
            if not(toBeAddedTo1 is None):
                if is_avg():
                    toBeAddedTo1[x][cc] = toBeAddedTo1[x][cc] + toBeAvg[x][cc]
                else:
                    toBeAddedTo1[x][cc] = toBeAddedTo1[x][cc] * toBeAvg[x][cc]
            if not(toBeAddedTo2 is None):
                if is_avg():
                    toBeAddedTo2[x][cc] = toBeAddedTo2[x][cc] + toBeAvg[x][cc]
                else:
                    toBeAddedTo2[x][cc] = toBeAddedTo2[x][cc] * toBeAvg[x][cc]                

def preprint(anything):
    if (is_html()):
        print("<pre>")                
    print(anything)
    if (is_html()):
        print("</pre>")

# WARNIGN WARNIGN WARNIGN WARNIGN virtkey is now virtualisation, and thus in first place in virtKey+keyPart+keyInterestedTypes
# WARNIGN that have to be fixed before moving to combinations. Propably te keyPart will need to be split to individual parts
# WARNIGN in addition the virtKey is iterable and its parts are taken...
# WARNIGN also jdk i sused as jdk in the JVbkmr constructor
def avgMapOfListsToJVbkmr(jdk, avgs, virtKey, keyPart):
    avgFinals = []
    for keyInterestedTypes, listOfVals in avgs.items():
        #jdks.proeprties and inside is very complicated key virtualisation_benchmark:key:metric:resultTyp=value
        y=-1
        for value in listOfVals:
            y+=1
            avgFinals.append(JVbkmr(jdk, virtKey[y]+keyPart+keyInterestedTypes, str(value), True))
    return avgFinals

def initMapOfLists(counterForItems, interestedTypes):
    mapOfLists={}
    for x in interestedTypes:
        mapOfLists[x]=[]
        for v in counterForItems:
            if is_avg():
                mapOfLists[x].append(float(0.0))
            else:
                mapOfLists[x].append(float(1.0))
    return mapOfLists
    

def jvbkmrprinter(allJdks, allBenchmarks,allVirtualisations, title1, title2, preffix, decorator, legend, interestedTypes, shift, avgs):
    #then follow passrate example on iterating jdk x benchamrk x jdk  as in passrates
    h1(title1)
    pre(title2)
    tableOfContext13(avgs)
    avgsOfAllJdksWithAll=initMapOfLists(allVirtualisations, interestedTypes)
    avgsOfAllJdks=initMapOfLists(allVirtualisations, interestedTypes)
    for jdk in allJdks:
        h1(jdk, jdk)
        if (jdk == "all"):
            pre("For those values, ALL jdks is moreover useless. But can serve as the ONE number if needed")
        avgsOfAllBenchmarks=initMapOfLists(allVirtualisations, interestedTypes)
        for benchmark in allBenchmarks:
            if (benchmark == "all"):
                continue
            h2(benchmark, jdk+"_"+benchmark)
            avgsOfAllMetrics=initMapOfLists(allVirtualisations, interestedTypes)
            for metric in allMetrics:
                h3(metricToString(metric), jdk+"_"+benchmark+"_"+metric)
                avgsOfAllKeys=initMapOfLists(allVirtualisations, interestedTypes)
                for key in allKeysPerBenchmark[benchmark]:
                    iddqd=jdk + "_" + benchmark + "_" + metric+"_"+key
                    h4(key, iddqd)
                    pre(jdk + " " + benchmark + " " + key + " where " + metricToString(metric))
                    drawChartForInterestedTypes(shift, allTypes, interestedTypes, jdk, key, None, benchmark, metric, preffix, decorator, legend, iddqd, avgsOfAllKeys, finals)
                avgAndAdd(avgsOfAllKeys, allKeysPerBenchmark[benchmark], avgsOfAllMetrics, None, interestedTypes, allVirtualisations)
                if (avgs):
                    iddqd=jdk + "_" + benchmark + "_" + metric+"_avg"
                    h4("avarage of all keys (benchmark meassured relativre accuracy)", iddqd)
                    preprint(avgsOfAllKeys)
                    avgFinals = avgMapOfListsToJVbkmr(jdk, avgsOfAllKeys, allVirtualisations, "_"+benchmark+":avg:"+metric+":" )
                    pre(jdk + " " + benchmark + " avg where " + metricToString(metric))
                    drawChartForInterestedTypes(shift, allTypes, interestedTypes, jdk, "avg", None, benchmark, metric, preffix, decorator, legend, iddqd, avgsOfAllKeys, avgFinals)
            avgAndAdd(avgsOfAllMetrics, allMetrics, avgsOfAllBenchmarks, None, interestedTypes, allVirtualisations);
            if (avgs):
                iddqd=jdk + "_" + benchmark + "_avg_avg"
                h4("avarage of all metrics from avarages of all keys", iddqd)
                preprint(avgsOfAllMetrics)
                avgFinals = avgMapOfListsToJVbkmr(jdk, avgsOfAllMetrics, allVirtualisations, "_"+benchmark+":avg:avg:" )
                pre(jdk + " " + benchmark + " avg avg")
                drawChartForInterestedTypes(shift, allTypes, interestedTypes, jdk, "avg", None, benchmark, "avg", preffix, decorator, legend, iddqd, avgsOfAllMetrics, avgFinals)   
        if (jdk == "all"):
            avgAndAdd(avgsOfAllBenchmarks, allBenchmarks, avgsOfAllJdksWithAll, None, interestedTypes, allVirtualisations)
        else:
            avgAndAdd(avgsOfAllBenchmarks, allBenchmarks, avgsOfAllJdksWithAll, avgsOfAllJdks, interestedTypes, allVirtualisations)
        if (avgs):
            iddqd=jdk + "_avg_avg_avg"
            h4("avarage of all benchamrks from avarages of all metrics and all keys", iddqd)
            preprint(avgsOfAllBenchmarks)
            avgFinals = avgMapOfListsToJVbkmr(jdk, avgsOfAllBenchmarks, allVirtualisations, "_avg:avg:avg:" )
            pre(jdk + " avg avg avg")
            drawChartForInterestedTypes(shift, allTypes, interestedTypes, jdk, "avg", None, "avg", "avg", preffix, decorator, legend, iddqd, avgsOfAllMetrics, avgFinals) 
    if (avgs):
        iddqd="avgX_avg_avg_avg"
        h4("avarage of all above (with all, thus wrong))", iddqd)
        preprint(avgsOfAllJdksWithAll)
        avgFinals = avgMapOfListsToJVbkmr("all", avgsOfAllJdksWithAll, allVirtualisations, "_avg:avg:avg:" )
        pre("avg(with all thus wrong) avg avg avg")
        drawChartForInterestedTypes(shift, allTypes, interestedTypes, "all", "avg", None, "avg", "avg", preffix, decorator, legend, iddqd, avgsOfAllMetrics, avgFinals)
        iddqd="avg_avg_avg_avg"
        h4("avarage of all above", iddqd)
        preprint(avgsOfAllJdks)
        avgFinals = avgMapOfListsToJVbkmr("all", avgsOfAllJdks, allVirtualisations, "_avg:avg:avg:" )
        pre("avg avg avg avg")
        drawChartForInterestedTypes(shift, allTypes, interestedTypes, "all", "avg", None, "avg", "avg", preffix, decorator, legend, iddqd, avgsOfAllMetrics, avgFinals)

def nonsensesToKey(selectHelper, key):
    if (selectHelper == "jbv"):
        return key.virtualizationFromKey
    if (selectHelper == "jvb"):
        return key.benchmarkFromKey
    if (selectHelper == "bvj"):
        return key.jdkFromDir
    if (selectHelper == "vbj"):
        return key.jdkFromDir


def passratesPrinter(allJdks, allBenchmarks, allVirtualisations, selectHelper):
    h2("crash rates - how much percent of the benchmarks actually finished. 100% all.")
    tableOfContext2(allJdks, allBenchmarks, selectHelper)
    for jdk in allJdks:
        h3(jdk, jdk+"-"+selectHelper)
        for benchmark in allBenchmarks:
            h4(benchmark, jdk+"_"+benchmark+"-"+selectHelper)
            if (benchmark == "all"):
                if (selectHelper == "jbv"):
                    fullSubset = selectCrashrate(jdk, None, None)
                if (selectHelper == "jvb"):
                    fullSubset = selectCrashrate(jdk, None, None)
                if (selectHelper == "bvj"):
                    fullSubset = selectCrashrate(None, None, jdk)
                if (selectHelper == "vbj"):
                    fullSubset = selectCrashrate(None, jdk, None)
                subset = [] # there are duplicated values. as we will count avg, we must remove them
                usedKeys=[]
                for x in fullSubset:
                    if not x.equalsKey() in usedKeys:
                        usedKeys.append(x.equalsKey())
                        subset.append(x)
                # no avg values for each benchmark to fullSubset
                fullSubset=[];
                for virtualisation in allVirtualisations:
                    value=0
                    count=0
                    for xjxbxv in subset:
                        inc = False;
                        if (selectHelper == "jbv"):
                            if (virtualisation == xjxbxv.virtualizationFromKey):
                                    inc = True
                        if (selectHelper == "jvb"):
                            if (virtualisation == xjxbxv.benchmarkFromKey):
                                    inc = True
                        if (selectHelper == "bvj"):
                            if (virtualisation == xjxbxv.jdkFromDir):
                                    inc = True
                        if (selectHelper == "vbj"):
                            if (virtualisation == xjxbxv.jdkFromDir):
                                    inc = True
                        if (inc):
                            value+=xjxbxv.value
                            count+=1
                    if (count==0):
                        value = 0;
                        count = 1;
                    if (selectHelper == "jbv"):
                        fullSubset.append(xJxBxV(jdk+"_all_"+virtualisation, virtualisation+"_all", str(value/count)+"%", True))
                    if (selectHelper == "jvb"):
                        fullSubset.append(xJxBxV(jdk+"_"+virtualisation+"_all", "all_"+virtualisation, str(value/count)+"%", True))
                    if (selectHelper == "bvj"):
                        fullSubset.append(xJxBxV(jdk+"_all_"+virtualisation, virtualisation+"_all", str(value/count)+"%", True))#?!?!!? most likely very wrong
                    if (selectHelper == "vbj"):
                        fullSubset.append(xJxBxV(virtualisation+"_all_"+jdk, jdk+"_all", str(value/count)+"%", True))
            else:
                if (selectHelper == "jbv"):
                    fullSubset = selectCrashrate(jdk, None, benchmark)
                if (selectHelper == "jvb"):
                    fullSubset = selectCrashrate(jdk, benchmark, None)
                if (selectHelper == "bvj"):
                    fullSubset = selectCrashrate(None, benchmark, jdk)
                if (selectHelper == "vbj"):
                    fullSubset = selectCrashrate(None, jdk, benchmark)
            fullSubset = sorted(fullSubset,  key=lambda key: nonsensesToKey(selectHelper, key))
            reSorted = sorted(fullSubset,  key=lambda key: key.value)
            subset = [] # there are duplicated values. In addition, plot is trasnforming list to set!
            usedKeys=[]
            for x in fullSubset:
                if not nonsensesToKey(selectHelper, x) in usedKeys:
                    usedKeys.append(nonsensesToKey(selectHelper,x))
                    if (selectHelper == "jvb" and x.benchmarkFromKey == "all"):
                        continue # we have added articicial all to et avgs above, it hav eno value
                    subset.append(x)
            reSorted = sorted(subset,  key=lambda key: key.value, reverse=True)
            xAxe=list(map(lambda xjxbxv: nonsensesToKey(selectHelper, xjxbxv), subset))
            yAxe = list(map(lambda xjxbxv: xjxbxv.value, subset))
            if (is_html()): 
                    print("<pre>") 
            for item in subset:
                print(str(item.value)+"% "+nonsensesToKey(selectHelper, item))
            print("--reordered--")
            for item in reSorted:
                print(str(item.value)+"% "+nonsensesToKey(selectHelper, item))
            if (is_html()): 
                print("</pre>")
            create_figure(xAxe, yAxe, "pass rate", "%", "passrate_"+jdk+"_"+benchmark+"_"+selectHelper, True)


passrates = [];
finals = []
allJdks = {}
allVirtualisations = {}
allBenchmarks = {}
allKeysPerBenchmark = {}
allMetrics = {"set"}
allMetrics.clear()
allTypes = {"set"}
allTypes.clear()
path="_pregenerated_reports"
for parentdir, dirs, files in os.walk(path, topdown=False):
    for name in files:
        filename = os.path.join(parentdir, name)
        if (filename.endswith(".properties.sort.uniq")):
            if (name == "passrates.properties.sort.uniq"):
                #eprint("found: " + name + " in " + parentdir);
                readPassRates(parentdir, filename, name)
            else:
                #eprint("found holly grail of " + name +" in " + parentdir)
                readFinals(parentdir, filename, name)
eprint("avg  : " + str(is_avg()) + "; geom : " + str(not is_avg()))
eprint("loaded passrates: " + str(len(passrates)))
eprint("loaded finals: " + str(len(finals)))
allJdks=sorted(allJdks);
eprint(allJdks)
allVirtualisations=sorted(allVirtualisations);
eprint(allVirtualisations)
allBenchmarks=sorted(allBenchmarks);
eprint(allBenchmarks)
eprint(allKeysPerBenchmark)
allMetrics=sorted(allMetrics);
eprint(allMetrics)
allTypes=sorted(allTypes);
eprint(allTypes)

absVals=["MIN", "MAX", "AVG", "MED"]
allAbsLegend="min (blue) ; max (orange) ; avg(green) ; med(red)",
relVals=['MAX-MIN', 'MIN-MED', 'MIN-MAX','MAX-AVG', 'MAX-MED','AVG-MED', 'MIN-AVG']
allRelLegend="MAX-MIN(blue);MIN-MED(orange);MIN-MAX(green);MAX-AVG(red);MAX-MED(purple);AVG-MED(brown);MIN-AVG(pink)"

SCENARIO=parse_number(sys.argv[1])

if (SCENARIO ==  1 or SCENARIO ==  1.1):
    jvbkmrprinter(
        allJdks, allBenchmarks,allVirtualisations,
        "absolute values of benchmarks per virtualisation",
        "time and other 'less is better` are shown inverted, so the view of charts is comaprable",
        "abs_",
        "",
        allAbsLegend,
        absVals,
        False,
        True
        )

if (SCENARIO ==  3 or SCENARIO ==  3.1):
    jvbkmrprinter(
        allJdks, allBenchmarks,allVirtualisations,
        "relative accuracy of benchmarks per virtualisation. Most pointable is MIN-MAX and MAX-MIN.",
        "The values are slightly shifted, so they can be readable even if linnes are identical",
        "rel_",
        "%",
        allRelLegend,
        relVals,
        True,
        True
        )

if (SCENARIO ==  2):
    ahref("Stabilities of virtualisations  -solution 1 (see all/all)", "jbv");tag("br","")
    ahref("Stabilities of benchmarks", "jvb");tag("br","")
    ahref("Stabilities of jdks 1", "bvj");tag("br","")
    ahref("Stabilities of jdks 2", "vbj");tag("br","")
    tag("hr","")
    h1("Stabilities of virtualisations", "jbv")
    passratesPrinter(allJdks, allBenchmarks, allVirtualisations, "jbv")
    h1("Stabilities of benchmarks", "jvb")
    bb=[];
    bb.extend(allVirtualisations)
    bb.append("all");
    passratesPrinter(allJdks, bb, allBenchmarks, "jvb")
    h1("Stabilities of jdks 1 (missing final averaging by design)", "bvj") #thi (bvj) two (and vbj) are actually the same. bvj misses the all section
    passratesPrinter(allBenchmarks, allVirtualisations, allJdks, "bvj")
    h1("Stabilities of jdks 2", "vbj")
    passratesPrinter(allVirtualisations, allBenchmarks, allJdks, "vbj")  #we keep both, as it is inverted view
