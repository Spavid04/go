executableExtensions = ["exe", "cmd", "bat", "py", "jar"]
folders_to_check = [
    ]








import subprocess
import os
import sys
import io
import tempfile
import json
import re
import threading
import difflib
import ctypes
import hashlib
from datetime import datetime
import time
import gzip
import math

def Cprint(para = ""):
    try:
        if quiet:
            return
    except:
        pass
    print(para);

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

kernel32 = ctypes.windll.kernel32
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32 = ctypes.windll.user32
user32.GetClipboardData.restype = ctypes.c_void_p
def get_clipboard_text():
    user32.OpenClipboard(0)
    try:
        if user32.IsClipboardFormatAvailable(1): #CF_TEXT
            data = user32.GetClipboardData(1) #CF_TEXT
            data_locked = kernel32.GlobalLock(data)
            text = ctypes.c_char_p(data_locked)
            value = text.value
            kernel32.GlobalUnlock(data_locked)
            return value
    finally:
        user32.CloseClipboard()

configFilePath = os.path.join(tempfile.gettempdir(), ".tree")

def ParallelRunThread(stream, shouldRedrawEvent, id, outStringArray):
    
    for line in iter(stream.readline, ''):
        outStringArray[id] = line.rstrip()
        shouldRedrawEvent.set()        
    
    outStringArray[id] = None

def ParallelRunPrinter(shouldRedrawEvent, outStringArray, quitEvent):
    maxStringLen = 0
    
    if not quiet:
        os.system("cls")

    while True:
        if shouldRedrawEvent.wait(0.010):
            shouldRedrawEvent.clear()
            
            if not quiet:
                os.system("cls")
            
            maxStringLen = max(maxStringLen, max([len(s) for s in outStringArray if s]+[0]))
            done = 0
            
            for line in outStringArray:
                if line:
                    Cprint(line.ljust(maxStringLen))
                    done += 1
            
            Cprint("[{}]\t/\t[{}]".format(len(outStringArray)-done, len(outStringArray)))
            Cprint("[{}] chunks left in queue".format(chunksLeft-1))
            
            time.sleep(0.500)
        else:
            if quitEvent.is_set():
                return

def ParallelRun(toRun):
    shouldRedrawEvent = threading.Event()
    outStringArray = [""]*len(toRun)
    subProcesses = [None]*len(toRun)
    
    quitEvent = threading.Event()
    
    printer = threading.Thread(target=ParallelRunPrinter, args=(shouldRedrawEvent, outStringArray, quitEvent))
    printer.daemon = True
    printer.start()
    
    for i in range(len(toRun)):
        subProcesses[i] = subprocess.Popen(toRun[i][0], shell=True, stdin=sys.stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=toRun[i][1], universal_newlines=True, bufsize=1)   
    
        t = threading.Thread(target=ParallelRunThread, args=(subProcesses[i].stdout, shouldRedrawEvent, i, outStringArray))
        t.daemon = True
        t.start()
        
        t = threading.Thread(target=ParallelRunThread, args=(subProcesses[i].stderr, shouldRedrawEvent, i, outStringArray))
        t.daemon = True
        t.start()
    
    for i in range(len(toRun)):
        subProcesses[i].wait()
    
    quitEvent.set()
    printer.join()

def invalidArgsAndHelp():
    Cprint("This script finds an executable file in a directory list and runs it.")
    Cprint()
    Cprint("go [/go_argument1] [/go_argument2] ... (exact filename OR regex) [target args] ...")
    Cprint()
    Cprint("By default, it only searches (non-recursively) in the PATH environment variable.")
    Cprint("Directories to search for and executable extensions can also be edited in the script file.")
    Cprint("Added directories are searched recursively.")
    Cprint("Current configuration file path: {}".format(configFilePath))
    Cprint()
    Cprint("Avaliable go_arguments:")
    Cprint()
    Cprint("/quiet        : Supresses any messages (but not exceptions) from this script.")
    Cprint("                /y should be considered when using this parameter")
    Cprint("/y            : Suppress inputs by answering \"yes\" (or the equivalent).")
    Cprint("/cd           : Changes the working directory to the target file's directory before running.")
    Cprint("                By default, the working directory is the one that this script is started in.")
    Cprint("                After running the script, it returns the working directory to the original one.")
    Cprint("/parse        : Forces the recreation of the cached file tree stored in the configuration file.")
    Cprint("                Auto-triggered when the last parse has been performed over a day (24h) ago.")
    Cprint("                Auto-triggered when the directory or extension list is differnt.")
    Cprint("/nopath       : Disables searching in the \"PATH\" environment variable.")
    Cprint("/reset        : Resets (deletes) the configuration file before all actions.")
    Cprint("/parallel     : Starts all instances, and then waits for all. Valid only with /*apply argument.")
    Cprint("/nowait       : Does not wait for the started process to end. This implies /parallel.")
    Cprint("/nth-XX       : Runs the nth file found. (specified by the 0-indexed XX suffix)")
    Cprint("                Avaliable when multiple files with the same name have been matched.")
    Cprint("/expand       : Expands environment variables in the final executable's argument list.")
    Cprint("/admin        : Runs this script (and the target) with the highest privileges.")
    Cprint("/repeat-XX    : Repeats the execution XX times.")
    Cprint("/rollover     : Modifies apply parameters to run as many times as possible, repeating source lists that are smaller.")
    Cprint("/batch-XX     : Batches parallel runs in sizes of XX. Valid only after /parallel.")
    Cprint("/addE-XXXX    : Temporarily adds the extension to the executable extensions list.")
    Cprint("/remE-XXXX    : Temporarily removes the extension from the executable extensions list.")
    Cprint("/addD-XXXX    : Temporarily adds the directory to the searched directories list.")
    Cprint("/remD-XXXX    : Temporarily removes the directory from the searched directories list.")
    Cprint("/list         : Lists any reachable matching files.")
    Cprint("/regex        : Matches the files by regex instead of exact filenames.")
    Cprint("                If enabled, the pattern should be enclosed in quotes.")
    Cprint("/[cf]apply    : For every line in the specified source, runs the target with the line appended as arguments.")
    Cprint("                One of either C(lipboard) or F(ile) must be specified.")
    Cprint("                A 0-based index can be appended like -XX to specify where to insert the new argument. Defaults to end.")
    Cprint("                If F is specified, a file must be appended to the argument like -\"path\".")
    Cprint("                Multiple apply parameters are supported, but the fewest of the sources will be run.")
    Cprint("                In this case, the resulting parameters are created in the input order, including growing insert indexes.")
    Cprint("/show         : Display the path of the executable that will be run, along with its arguments. Does not run the target.")
    Cprint()
    Cprint()
    Cprint(">>>Invalid arguments provided!")
    
    exit()

if len(sys.argv) <= 1:
    invalidArgsAndHelp()

scriptParameters = 0
shouldRewriteConfig = False

applyRegex = re.compile(r"^\/([cf])apply(-\d+)?(-.+)?$", re.I)

quiet = False
changeDir = False
useRegex = False
shouldRecreateDirectoryStructure = False
searchInPath = True
parallel = False
waitForEnd = True
nthFile = -1
sameArguments = False
expandVariables = False
listFiles = False
asAdmin = False
extraArgsList = [] #tuples of (list of strings, int) = argList,targetIndex
suppressWithYes = False
repeatCount = 1
showOnly = False
rollover = False
batchCount = 0

while True:
    if scriptParameters + 1 >= len(sys.argv):
        break
    
    arg = sys.argv[scriptParameters + 1]
    if arg.lower() == "/quiet":
        quiet = True
    elif arg.lower() == "/y":
        suppressWithYes = True
    elif arg.lower() == "/cd":
        changeDir = True
    elif arg.lower() == "/regex":
        useRegex = True
    elif arg.lower() == "/parse":
        shouldRecreateDirectoryStructure = True
    elif arg.lower() == "/nopath":
        searchInPath = False
    elif arg.lower() == "/parallel":
        parallel = True
    elif arg.lower() == "/nowait":
        waitForEnd = False
        parallel = True
    elif arg.lower().startswith("/nth-"):
        nthIndex = arg[5:]
        if nthIndex != "":
            nthFile = int(nthIndex)
    elif arg.lower() == "/expand":
        expandVariables = True
    elif arg.lower() == "/list":
        listFiles = True
    elif arg.lower() == "/admin":
        asAdmin = True
    elif arg.lower().startswith("/repeat-"):
        t = arg[8:]
        if t != "":
            repeatCount = int(t)
    elif arg.lower() == "/rollover":
        rollover = True
    elif arg.lower().startswith("/batch-"):
        t = arg[7:]
        if t != "":
            batchCount = int(t)
    elif arg.lower().startswith("/adde-"):
        ext = arg[6:].lower()
        if ext.startswith("."):
            ext = ext[1:]
        executableExtensions.append(ext)
    elif arg.lower().startswith("/reme-"):
        ext = arg[6:].lower()
        if ext.startswith("."):
            ext = ext[1:]
        if ext in executableExtensions:
            executableExtensions.remove(ext)
    elif arg.lower().startswith("/addd-"):
        dir = arg[6:]
        folders_to_check.append(dir)
        shouldRecreateDirectoryStructure = True
    elif arg.lower().startswith("/remd-"):
        dir = arg[6:]
        if dir in folders_to_check:
            folders_to_check.remove(dir)
            shouldRecreateDirectoryStructure = True
    elif arg.lower() == "/reset":
        if os.path.isfile(configFilePath):
            os.remove(configFilePath)
    elif applyRegex.fullmatch(arg):
        options = applyRegex.fullmatch(arg).groups()
        argsFromSource = []
        argsTargetIndex = sys.maxsize
        
        if options[0].lower()=="c":
            cdata = get_clipboard_text()
            
            if cdata:
                cdata = cdata.decode("utf-8")
                argsFromSource = [line for line in cdata.split("\r\n") if len(line) > 0]
        else:
            argsFromSource = [line.strip() for line in open(options[2][1:])]
        
        if options[1]:
            argsTargetIndex = int(options[1][1:])
        
        extraArgsList.append((argsFromSource, argsTargetIndex))
    elif arg.lower() == "/show":
        showOnly = True
    else:
        break
    scriptParameters += 1

if len(sys.argv) <= 1 + scriptParameters:
    invalidArgsAndHelp()

targetListSize = 0
if len(extraArgsList) >= 1:
    #resize all lists to match the smallest one, used only if /rollover is not specified, otherwise the largest
    
    if rollover:
        targetListSize = len(max(extraArgsList, key= lambda x : len(x[0]))[0])
    else:
        targetListSize = len(min(extraArgsList, key= lambda x : len(x[0]))[0])
    
    if targetListSize > 50:
        Cprint(">>>More than 50 lines ({}) present in the source".format(targetListSize))
        if suppressWithYes:
            Cprint(">>>Suppressed with yes")
        else:
            Cprint(">>>Continue? y(default on empty)/n")
            res = input().lower()
            if len(res) > 0 and res[0] != "y":
                Cprint(">>>Aborted")
                exit()
else:
    targetListSize = 1

if asAdmin:
    try:
        hasAdminPrivilege = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        hasAdminPrivilege = False
    
    if not hasAdminPrivilege:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        exit()

if not os.path.isfile(configFilePath):
    shouldRecreateDirectoryStructure = True
else:
    with gzip.GzipFile(configFilePath, "r") as f:
        json_str = f.read().decode("utf-8")
        ((lastParse, oldDirs, oldExts, lastArgsMd5), _) = json.loads(json_str)
    if (datetime.now() - datetime.fromtimestamp(lastParse)).days >= 1:
        shouldRecreateDirectoryStructure = True
    if tuple(folders_to_check) != tuple(oldDirs) or tuple(executableExtensions) != tuple(oldExts):
        shouldRecreateDirectoryStructure = True
    if lastArgsMd5 == hashlib.md5(("\n".join(sys.argv)).encode("utf-8")).hexdigest():
        sameArguments = True
    else:
        shouldRewriteConfig = True

files = []

if shouldRecreateDirectoryStructure:
    if searchInPath:
        for pathDir in os.environ["PATH"].split(";"):
            for (r,_,f) in os.walk(pathDir):
                for fl in f:
                    (_, extension) = os.path.splitext(fl)
                    extension = extension.lower()
                    
                    if extension[1:] not in executableExtensions:
                        continue
                    
                    files.append(os.path.abspath(os.path.join(r, fl)))
                break #PATH should not be recursive
    
    for folder in folders_to_check:
        try:
            for (r,_,f) in os.walk(folder):
                for fl in f:
                    (_, extension) = os.path.splitext(fl)
                    extension = extension.lower()
                    
                    if extension[1:] not in executableExtensions:
                        continue
                    
                    files.append(os.path.abspath(os.path.join(r, fl)))
        except:
            pass
    
    dup = set()
    files = [x for x in files if x.lower() not in dup and not dup.add(x.lower())]
    
    with gzip.GzipFile(configFilePath, "w") as f:
        json_str = json.dumps(
                        ((datetime.now().timestamp(), tuple(folders_to_check), tuple(executableExtensions), hashlib.md5(("\n".join(sys.argv)).encode("utf-8")).hexdigest()), files)
                    ).encode("utf-8")
        f.write(json_str)
else:
    with gzip.GzipFile(configFilePath, "r") as f:
        json_str = f.read().decode("utf-8")
        (_, files) = json.loads(json_str)

if shouldRewriteConfig:
    with gzip.GzipFile(configFilePath, "r") as f:
        json_str = f.read().decode("utf-8")
        ((a11, a12, a13, a14), a2) = json.loads(json_str)
    with gzip.GzipFile(configFilePath, "w") as f:
        json_str = json.dumps(((a11, a12, a13, hashlib.md5(("\n".join(sys.argv)).encode("utf-8")).hexdigest()), a2)).encode("utf-8")
        f.write(json_str)

fileToRun = sys.argv[1 + scriptParameters].lower()
parameters = sys.argv[2 + scriptParameters:]

regexCompiled = None
if useRegex:
    regexCompiled = re.compile(sys.argv[1 + scriptParameters], re.I)

if expandVariables:
    parameters = list([os.path.expandvars(param) for param in parameters])

matchedFiles = []
fuzzyMatchedFiles = []

for fullpath in files:
    (directory, filename) = os.path.split(fullpath)
    
    (filename, extension) = os.path.splitext(filename)
    
    directory = directory.lower()
    filename = filename.lower()
    extension = extension.lower()
    
    if useRegex:
        if regexCompiled.match(filename) or regexCompiled.match(filename+extension):
            matchedFiles.append(fullpath)
    else:
        if fileToRun == filename or fileToRun == (filename+extension):
            matchedFiles.append(fullpath)
        else:
            fuzzyMatchedFiles.append(
                ( #tuples of type (similarity, fullpath)
                    max(difflib.SequenceMatcher(None, filename, fileToRun).ratio(),
                        difflib.SequenceMatcher(None, filename+extension, fileToRun).ratio()),
                    fullpath
                )
            )

if listFiles:
    Cprint("\n".join(matchedFiles))
    exit()

fuzzyMatchedFiles = sorted([t for t in fuzzyMatchedFiles if t[0]>0.7], reverse=True, key=lambda x:x[0])[:5]

file = ""

if len(matchedFiles) == 1:
    file = matchedFiles[0]
elif len(matchedFiles) == 0:
    Cprint(">>>could not find file")
    if len(fuzzyMatchedFiles) > 0:
        Cprint("did you mean:")
        for (_, fmf) in fuzzyMatchedFiles:
            Cprint("    {0:24s} at {1}".format(os.path.split(fmf)[1], fmf))
else:
    if nthFile != -1:
        file = matchedFiles[nthFile]
    elif nthFile == -1 and sameArguments:
        Cprint(">>>multiple files found")
        Cprint("defaulted to [0]")
        file = matchedFiles[0]
    else:
        Cprint(">>>multiple files found")
        Cprint("run with the same arguments again to choose [0], or use /nth-XX to choose:")
        for i in range(0, len(matchedFiles)):
            Cprint("[{0:2d}]: {1}".format(i, matchedFiles[i]))

if file != "":
    Cprint("running: "+file)
    sys.stdout.flush()
    
    toRun = []
    
    for argIndex in range(targetListSize):
        arrangedParameters = list(parameters)
        
        for i in range(len(extraArgsList)):
            arrangedParameters.insert(extraArgsList[i][1], extraArgsList[i][0][argIndex % len(extraArgsList[i][0])])
        
        cwd = None
        if changeDir:
            cwd = os.path.dirname(file)
        
        toRun += [([file] +arrangedParameters, cwd)]
    
    if repeatCount > 1:
        toRun = toRun*repeatCount
    
    if batchCount == 0:
        batchCount = len(toRun)
    
    if showOnly:
        for chunk in batch(toRun, batchCount):
            Cprint("\n".join([str(x[0]) for x in chunk]))
            Cprint()
    else:
        if waitForEnd and parallel:
            chunksLeft = math.ceil(len(toRun) / batchCount)
            for chunk in batch(toRun, batchCount):
                ParallelRun(chunk)
                chunksLeft -= 1
        else:
            for (elToRun, cwd) in toRun:
                if waitForEnd and (not parallel):
                    subprocess.run(elToRun, shell=True, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, cwd=cwd)
                elif (not waitForEnd) and parallel:
                    subprocess.Popen(elToRun, shell=True, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, cwd=cwd)            
