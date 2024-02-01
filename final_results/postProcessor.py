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

# scenario 1: gathered absolute values from inverted_results/*properties.sort.uniq  
# min, max, avg, med
# thus we can show impact of virtualisation on performance

# scenario 2: gathered  vlaues from passrates.properties.sort.uniq (note there is trailing %:-/
# there we can show which jdk was most/less stable under which virtualisation
# there we can show, which virtualisation generally improveds stability, and which degraded it

#scenario 3: the final answer from inverted_results/*properties.sort.uniq
# here we have relative stability results per jdk and per virtualisation
# there is hidden final answer of imapct of (nested) virtualisation to accuracy

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
    def __init__(self, dirName, keyName, value):
        self.value = parse_number(re.sub("%","",value))
        self.originalDir = dirName
        self.originalKey = keyName
        #eprint(str(self.value) + " " + self.originalDir + " " + self.originalKey)
        # now parse origDir and Key. The final benchmark and virtualisation should match
        # if not, use one (and with other objects) use it consitently.
        # Benchmark name may contain several _ :(
        self.jdkFromDir = dirName.split("_")[0];  # eg jdk11, all, allJ
        self.jdkFromDir = sanitizeAll(self.jdkFromDir)
        initOrAdd(allJdks, self.jdkFromDir);
        self.benchmarkFromDir = dirName.split("_")[1]; 
        self.benchmarkFromDir = sanitizeAll(self.benchmarkFromDir)
        initOrAdd(allBenchmarks, self.benchmarkFromDir)
        # NO! this virt is not used in JVbkmr; dont use
        self.virtualizationFromDir = re.sub(self.jdkFromDir+"_"+self.benchmarkFromDir+"_", "", dirName) #container_results  containers_in_container_results
        self.benchmarkFromKey = self.originalKey.split("_")[-1];
        self.benchmarkFromKey = sanitizeAll(self.benchmarkFromKey)
        initOrAdd(allBenchmarks, self.benchmarkFromKey)
        #YES, this  is shared with JVbkmr; use this
        self.virtualizationFromKey = re.sub("_"+self.benchmarkFromKey, "", self.originalKey)  #container-results  containers_in_container
        self.virtualizationFromKey = sanitizeAll(self.virtualizationFromKey)
        initOrAdd(allVirtualisations, self.virtualizationFromKey)
        #eprint(niceString(self))

def niceString(self):
    return str(self.value) + " (" + self.jdkFromDir+ " " + self.benchmarkFromDir+" " + self.virtualizationFromDir + ") (" + self.virtualizationFromKey + " " +self.benchmarkFromKey+")"

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

    def __init__(self, fileName, keyName, value):
        self.value = parse_number(re.sub("%","",value))
        self.jdkFromName = re.sub("\.properties.*","",fileName)
        self.jdkFromName = sanitizeAll(self.jdkFromName)
        initOrAdd(allJdks, self.jdkFromName); # eg java-11
        self.originalKey = keyName
        #eprint(str(self.value) + " " + self.jdkFromName + " " + self.originalKey)
        # now parse originalKey
        splited = self.originalKey.split(":");
        self.resultType=splited[3]
        allTypes.add(self.resultType)
        self.metric=splited[2]
        allMetrics.add(self.metric)
        self.key=splited[1]
        if (self.key.find("Time")>=0):
            self.value=-1*self.value
        if (self.resultType.find("-")>=0):
            self.value=abs(self.value)
        virtAndbench=splited[0]
        self.benchmark = virtAndbench.split("_")[-1];
        self.benchmark = sanitizeAll(self.benchmark)
        initOrAdd(allBenchmarks, self.benchmark)
        if (self.benchmark in allKeysPerBenchmark):
            allKeysPerBenchmark[self.benchmark].add(self.key)
        else:
            allKeysPerBenchmark[self.benchmark]={self.key}
        self.virtualisation = re.sub("_"+self.benchmark, "", virtAndbench)  #container-results  containers_in_container
        self.virtualisation = sanitizeAll(self.virtualisation)
        initOrAdd(allVirtualisations, self.virtualisation)
        #eprint(niceString(self))
    
    def niceString(self):
        return str(self.value) +" " + self.jdkFromName + " (" + self.virtualisation+ " " + self.benchmark+" " + self.key + " " + self.metric + " " +self.resultType+")"

def initOrAdd(hashmap, key):
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

def selectFinals(jdkFromName, key, virtualisation, benchmark, metric, resultType):
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

def tableOfContext13():
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
                ole()
            ole()
        ole()
    ole()
    tag("hr","");

def tableOfContext2():
    olo()
    for jdk in allJdks:
        lio();ahref(jdk, jdk);lie()
        olo()
        for benchmark in allBenchmarks:
            lio();ahref(benchmark, jdk+"_"+benchmark);lie()
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
eprint("loaded passrates: " + str(len(passrates)))
eprint("loaded finals: " + str(len(finals)))
eprint(allJdks)
eprint(allVirtualisations)
eprint(allBenchmarks)
eprint(allKeysPerBenchmark)
eprint(allMetrics)
eprint(allTypes)

absVals=["MIN", "MAX", "AVG", "MED"]

SCENARIO=round(parse_number(sys.argv[1]))

if (SCENARIO ==  1):
    h1("absolute velues of benchmarks per virtualisation")
    pre("time and other 'less is better` are shown inverted, so the view of charts is comaprable")
    tableOfContext13()
    for jdk in allJdks:
        h1(jdk, jdk)
        if (jdk == "all"):
            pre("For those values, ALL jdks is moreover useless. But can serve as the ONE number if needed")
        for benchmark in allBenchmarks:
            if (benchmark == "all"):
                continue
            h2(benchmark, jdk+"_"+benchmark)
            for metric in allMetrics:
                h3(metricToString(metric), jdk+"_"+benchmark+"_"+metric)
                for key in allKeysPerBenchmark[benchmark]:
                    iddqd=jdk + "_" + benchmark + "_" + metric+"_"+key
                    h4(key, iddqd)
                    pre(jdk + " " + benchmark + " " + key + " where " + metricToString(metric))
                    if (is_html()): 
                            print("<pre>")  
                    fig_transfer = None
                    i=-1
                    for x in absVals:
                        i+=1
                        if x in allTypes:
                            subset = selectFinals(jdk, key, None, benchmark, metric, x)
                            # if to sort, then by virtualization name
                            subset = sorted(subset,  key=lambda r: r.virtualisation)
                            xAxe = list(map(lambda final: final.virtualisation, subset))
                            yAxe = list(map(lambda final: final.value, subset))
                            for item in subset:
                                print(x+ " " + str(item.value)+" "+item.virtualisation )
                            if (not (i == len(absVals)-1)):
                                fig_transfer = create_figure(xAxe, yAxe, "rewritten", key, "abs_"+iddqd, False, fig_transfer)
                            else:
                                create_figure(xAxe, yAxe, "min (blue) ; max (orange) ; avg(green) ; med(red)", key, "abs_"+iddqd, True, fig_transfer)
                                if (is_html()):
                                    print("</pre>")
                        else:
                            pre("missing value: " + x)

if (SCENARIO ==  2):
    h1("crash rates - how much percent of the benchmarks actually finished. 100% all.")
    tableOfContext2()
    for jdk in allJdks:
        h1(jdk, jdk)
        for benchmark in allBenchmarks:
            h2(benchmark, jdk+"_"+benchmark)
            if (benchmark == "all"):
                h3("all is not defined? TODO, resolve by manual select and some calcualtion")
                continue
            fullSubset = selectCrashrate(jdk, None, benchmark)
            fullSubset = sorted(fullSubset,  key=lambda key: key.virtualizationFromKey)
            reSorted = sorted(fullSubset,  key=lambda key: key.value)
            subset = [] # there are duplicated values. In addition, plot is trasnforming list to set!
            usedKeys=[]
            for x in fullSubset:
                if not x.virtualizationFromKey in usedKeys:
                    usedKeys.append(x.virtualizationFromKey)
                    subset.append(x)
            reSorted = sorted(subset,  key=lambda key: key.value, reverse=True)
            xAxe=list(map(lambda xjxbxv: xjxbxv.virtualizationFromKey, subset))
            yAxe = list(map(lambda xjxbxv: xjxbxv.value, subset))
            if (is_html()): 
                    print("<pre>") 
            for item in subset:
                print(str(item.value)+"% "+item.virtualizationFromKey)
            print("--reordered--")
            for item in reSorted:
                print(str(item.value)+"% "+item.virtualizationFromKey)
            if (is_html()): 
                print("</pre>")
            create_figure(xAxe, yAxe, "pass rate", "%", "passrate_"+jdk+"_"+benchmark, True)
