import ctypes
import difflib
import json
import os
import re
import subprocess
import threading
import time
import typing
import sys


def PrintHelp():
    print("The main use of this script is to find an executable and run it easily.")
    print("go [/go argument 1] [/go argument 2] ... <target> [target args] ...")
    print()
    print("By default, it only searches (non-recursively) in the %PATH% variable.")
    print(
        "Config files (default: go.config) can be used to specify \"TargetedExtensions\" and \"TargetedDirectories\".")
    print("Added directories are searched recursively.")
    print()
    print("Avaliable go arguments:")
    print()
    print("/config-XXXX  : Uses the specified config file.")
    print("/ext[+-]XXXX  : Adds or removes the extension to the executable extensions list.")
    print("/dir[+-]XXXX  : Adds or removes the directory to the searched directories list.")
    print()
    print("/regex        : Matches the files by regex instead of filenames.")
    print("/in-XXXX      : Allows an alternate way to choose ambiguous executables by specifying a path substring.")
    print("/nth-XX       : Runs the nth file found. (specified by the 0-indexed XX suffix)")
    print()
    print("/quiet        : Supresses any messages (but not exceptions) from this script. /yes is implied.")
    print("/yes          : Suppress inputs by answering \"yes\" (or the equivalent).")
    print("/echo         : Echoes the command to be run, including arguments, before running it.")
    print("/dry          : Marks runs as dry. Dry runs do not actually run the target executable.")
    print("/list         : Alias for /echo and /dry.")
    print()
    print("/cd           : Changes the working directory to the target file's directory before running.")
    print("                By default, the working directory is the one that this script is started in.")
    print("                After running the script, it returns the working directory to the original one.")
    print("/elevate      : Requests elevation before running the target.")
    print("/nowait       : Does not wait for the started process to end. This implies /parallel.")
    print("/parallel     : Starts all instances, and then waits for all. Valid only with /*apply argument.")
    print("/limit-XX     : Limits parallel runs to have at most XX targets running at once.")
    print("/batch-XX     : Batches parallel runs in sizes of XX. Valid only after /parallel.")
    print()
    print("/repeat-XX    : Repeats the execution XX times.")
    print(
        "/rollover     : Modifies apply parameters to run as many times as possible, repeating source lists that are smaller.")
    print("/[cfgip]apply : For every line in the specified source, runs the target with the line added as arguments.")
    print("                If no inline markers (see below) are specified, all arguments are appended to the end.")
    print("                One of either C(lipboard), F(ile), G(o), I(mmediate) or P(ipe) must be specified.")
    print("                Optionally accepts a python-like list indexer before the optional \"argument\", like -[XXX].")
    print("                Types of apply:")
    print("                    C: reads the input from the clipboard")
    print("                    F: reads the lines of a file, specified with -\"path\"")
    print("                    G: reads the output lines of a go command, specified with -\"command\"")
    print("                    I: reads the immediate string as a comma separated list")
    print("                    P: reads the input lines from stdin")
    print("                Inline markers:")
    print("                    Syntax: %%[index of apply source]%%")
    print("                    Specifies where to append the apply lists. Can use the same list more times.")
    print("                    If a number is specified, it takes that list, otherwise it uses the next unused one.")


class Utils(object):
    @staticmethod
    def ParseDirectoriesForFiles(directories: typing.List[str], extensions: typing.List[str], recursive: bool) -> \
            typing.List[str]:
        matchingFiles = []

        for directory in directories:
            for (root, _, files) in os.walk(directory):
                for file in files:
                    (_, extension) = os.path.splitext(file)
                    extension = extension.lower()

                    if extension not in extensions:
                        continue

                    abspath = os.path.abspath(os.path.join(root, file))

                    if abspath in matchingFiles:
                        continue

                    matchingFiles.append(abspath)

                if not recursive:
                    break

        return matchingFiles

    _Compare_RegexObject = None

    @staticmethod
    def ComparePathAndFile(path: str, fileOrRegex: str, asRegex: bool) -> float:
        (_, fullFilename) = os.path.split(path)
        fullFilename = fullFilename.lower()
        (filename, _) = os.path.splitext(fullFilename)

        if asRegex:
            if Utils._Compare_RegexObject is None:
                Utils._Compare_RegexObject = re.compile(fileOrRegex, re.I)

            if Utils._Compare_RegexObject.match(filename) or Utils._Compare_RegexObject.match(fullFilename):
                return 1
            else:
                return 0
        else:
            fileOrRegex = fileOrRegex.lower()

            return max(difflib.SequenceMatcher(None, filename, fileOrRegex).ratio(),
                       difflib.SequenceMatcher(None, fullFilename, fileOrRegex).ratio())

    @staticmethod
    def PathContains(path: str, substring: str) -> bool:
        (directory, _) = os.path.splitext(path)

        return substring.lower() in directory.lower()

    _Clipboard_ValuesInitialized = False
    _Clipboard_Kernel32 = None
    _Clipboard_User32 = None

    @staticmethod
    def GetClipboardText() -> str:
        if not Utils._Clipboard_ValuesInitialized:
            Utils._Clipboard_Kernel32 = ctypes.windll.kernel32
            Utils._Clipboard_Kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            Utils._Clipboard_Kernel32.GlobalLock.restype = ctypes.c_void_p
            Utils._Clipboard_Kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            Utils._Clipboard_User32 = ctypes.windll.user32
            Utils._Clipboard_User32.GetClipboardData.restype = ctypes.c_void_p

            Utils._Clipboard_ValuesInitialized = True

        Utils._Clipboard_User32.OpenClipboard(0)
        try:
            if Utils._Clipboard_User32.IsClipboardFormatAvailable(1):  # CF_TEXT
                data = Utils._Clipboard_User32.GetClipboardData(1)  # CF_TEXT
                data_locked = Utils._Clipboard_Kernel32.GlobalLock(data)
                text = ctypes.c_char_p(data_locked)
                value = text.value
                Utils._Clipboard_Kernel32.GlobalUnlock(data_locked)
                return value.decode("utf-8")
        finally:
            Utils._Clipboard_User32.CloseClipboard()

        return ""

    @staticmethod
    def ReadStdin() -> typing.List[str]:
        lines = []

        while True:
            try:
                line = input()
            except:
                break

            if not line:
                continue

            lines.append(line)

        return lines

    @staticmethod
    def ReadAllLines(file: str) -> typing.List[str]:
        with open(file, "utf-8") as f:
            return f.readlines()

    @staticmethod
    def CaptureOutput(command: str) -> typing.List[str]:
        lines = []

        process = subprocess.Popen("go " + command, shell=True, stdout=subprocess.PIPE)
        for line in process.stdout:
            lines.append(line.rstrip().decode("utf-8"))

        return lines

    @staticmethod
    def EnsureAdmin():
        hasAdmin = False

        try:
            hasAdmin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            hasAdmin = False

        if not hasAdmin:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            exit()

    @staticmethod
    def Batch(list: typing.List[object], batchSize: int) -> typing.Generator[typing.List[object], None, None]:
        length = len(list)
        for i in range(0, length, batchSize):
            yield list[i:min(i + batchSize, length)]


class GoConfig:
    _ApplyRegex = re.compile("^/([cfgip])apply(?:-(\\[[-0-9:]+?\\]))?(?:-(.+))?$", re.I)

    def __init__(self):
        self.ConfigFile = "go.config"

        self.TargetedExtensions = [".exe", ".cmd", ".bat", ".py"]
        self.TargetedDirectories = []

        self.ReloadConfig(False)

        self.RegexTargetMatch = False
        self.DirectoryFilter = None
        self.NthMatch = None

        self.QuietGo = False  # todo
        self.EchoTarget = False
        self.DryRun = False
        self.SuppressPrompts = False

        self.ChangeWorkingDirectory = False
        self.WaitForExit = True
        self.Parallel = False
        self.Batched = False
        self.ParallelLimit = None

        self.ApplyLists = []  # type: typing.List[GoConfig.ApplyElement]
        self.Rollover = False
        self.RepeatCount = None

    def ReloadConfig(self, overwriteSettings: bool):
        path = self.ConfigFile

        if os.path.abspath(path).lower() != path.lower():
            scriptPath = __file__
            try:
                scriptPath = os.readlink(scriptPath)
            except:
                pass

            scriptDir = os.path.split(scriptPath)[0]

            path = os.path.join(scriptDir, path)

        targetedExtensions = []
        targetedDirectories = []

        with open(path, "r") as f:
            config = json.load(f)

            targetedExtensions = config["TargetedExtensions"]
            targetedDirectories = config["TargetedDirectories"]

        if overwriteSettings:
            self.TargetedExtensions = targetedExtensions
            self.TargetedDirectories = targetedDirectories
        else:
            self.TargetedExtensions.extend(targetedExtensions)
            self.TargetedDirectories.extend(targetedDirectories)

    class ApplyElement:
        def __init__(self, sourceType: str, indexer: typing.Optional[str] = None, source: typing.Optional[str] = None):
            self.SourceType = sourceType
            self.Indexer = eval("lambda x : x" + indexer) if indexer else None
            self.Source = source

            self.List = None

    def TryParseArgument(self, argument: str) -> bool:
        lower = argument.lower()

        if lower.startswith("/config-"):
            path = argument[8:]
            self.ConfigFile = path
            self.ReloadConfig(True)
        elif lower.startswith("/dir"):
            action = lower[4]
            path = lower[5:]

            if action == '-':
                if path in self.TargetedDirectories:
                    self.TargetedDirectories.remove(path)
            else:
                if path not in self.TargetedDirectories:
                    self.TargetedDirectories.append(path)
        elif lower.startswith("/ext"):
            action = lower[4]
            extension = lower[5:]

            if action == '-':
                if extension in self.TargetedExtensions:
                    self.TargetedExtensions.remove(extension)
            else:
                if extension not in self.TargetedExtensions:
                    self.TargetedExtensions.append(extension)

        elif lower == "/regex":
            self.RegexTargetMatch = True
        elif lower.startswith("/in-"):
            self.DirectoryFilter = argument[4:]
        elif lower.startswith("/nth"):
            self.NthMatch = 0

            nthAsString = lower[5:]
            if len(nthAsString) > 0:
                self.NthMatch = int(nthAsString)

        elif lower == "/quiet":
            self.QuietGo = True
            self.TryParseArgument("/yes")
        elif lower == "/list":
            self.TryParseArgument("/echo")
            self.TryParseArgument("/dryrun")
        elif lower == "/echo":
            self.EchoTarget = True
        elif lower == "/dryrun":
            self.DryRun = True
        elif lower == "/yes":
            self.SuppressPrompts = True

        elif lower == "/elevate":
            Utils.EnsureAdmin()
        elif lower == "/cd":
            self.ChangeWorkingDirectory = True
        elif lower == "/nowait":
            self.WaitForExit = False
        elif lower == "/parallel":
            self.Parallel = True
        elif lower == "/batch":
            self.Batched = True
        elif lower.startswith("/limit-"):
            self.ParallelLimit = int(lower[7:])

        elif GoConfig._ApplyRegex.match(lower):
            groups = GoConfig._ApplyRegex.match(lower).groups()

            type = groups[0]
            indexer = groups[1]
            source = groups[2]

            if type == 'c' or type == 'p':
                self.ApplyLists.append(GoConfig.ApplyElement(type, indexer))
            elif type == 'f' or type == 'g' or type == 'i':
                self.ApplyLists.append(GoConfig.ApplyElement(type, indexer, source))
            else:
                return False
        elif lower == "/rollover":
            self.Rollover = True
        elif lower.startswith("/repeat-"):
            self.RepeatCount = int(lower[8:])

        else:
            return False

        return True

    def Validate(self) -> bool:
        if self.DryRun and not self.EchoTarget:
            print(">>>invalid arguments: /dry requires /echo")
            return False

        if self.Parallel and not self.WaitForExit:
            print(">>>/nowait doesn't do anything with /parallel")

        if self.Batched and not self.ParallelLimit:
            print(">>>/batch requires /limit to be specified")
            return False

        return True

    def FetchFiles(self) -> typing.List[str]:
        files = []

        files = Utils.ParseDirectoriesForFiles(os.environ["PATH"].split(";"), self.TargetedExtensions, False)

        for file in Utils.ParseDirectoriesForFiles(self.TargetedDirectories, self.TargetedExtensions, True):
            if file not in files:
                files.append(file)

        return files

    def ProcessApplyArguments(self, targetArguments: typing.List[str]) -> typing.List[typing.List[str]]:
        if len(self.ApplyLists) == 0:
            repeat = 1 if self.RepeatCount is None else self.RepeatCount
            return [[x] * repeat for x in targetArguments]

        # region generate lists

        for applyArgument in self.ApplyLists:
            if applyArgument.SourceType == 'c':
                applyArgument.List = [x for x in Utils.GetClipboardText().split("\r\n") if len(x) > 0]
            elif applyArgument.SourceType == 'p':
                applyArgument.List = Utils.ReadStdin()
            elif applyArgument.SourceType == 'f':
                applyArgument.List = Utils.ReadAllLines(applyArgument.Source)
            elif applyArgument.SourceType == 'g':
                applyArgument.List = Utils.CaptureOutput(applyArgument.Source)
            elif applyArgument.SourceType == 'i':
                applyArgument.List = applyArgument.Source.split(',')

            if applyArgument.Indexer:
                applyArgument.List = applyArgument.Indexer(applyArgument.List)

        # endregion

        # region adjust lengths

        if self.RepeatCount is not None and self.RepeatCount >= 2:
            for applyArgument in self.ApplyLists:
                originalLength = len(applyArgument.List)

                for i in range(self.RepeatCount - 1):
                    applyArgument.List.extend(applyArgument.List[:originalLength])

        if self.Rollover:
            maxOriginalLength = max(len(x.List) for x in self.ApplyLists)

            for applyArgument in self.ApplyLists:
                originalLength = len(applyArgument.List)

                while len(applyArgument.List) < maxOriginalLength:
                    applyArgument.List.extend(applyArgument.List[:originalLength])

        minLength = min(len(x.List) for x in self.ApplyLists)

        for applyArgument in self.ApplyLists:
            if len(applyArgument.List) > minLength:
                applyArgument.List = applyArgument.List[:minLength]

        # endregion

        newArguments = []

        # region process inline markers

        self._ApplyListsUsed = [False] * len(self.ApplyLists)
        self._CurrentApplyListIndex = 0

        for targetArgument in targetArguments:
            newArgument = self._ProcessInlineMarker(targetArgument)
            newArguments.append(newArgument)

        applyLength = 1 if len(self.ApplyLists) == 0 else len(self.ApplyLists[0].List)

        for i in range(len(newArguments)):
            if isinstance(newArguments[i], str):
                newArguments[i] = [newArguments[i]] * applyLength

        for i in range(len(self.ApplyLists)):
            if not self._ApplyListsUsed[i]:
                newArguments.append(self.ApplyLists[i].List)

        # endregion

        return newArguments

    _InlineMarkerRegex = re.compile(r"^%%(\d*)%%$", re.I)

    # todo search for in-quote markers too
    def _ProcessInlineMarker(self, argument: str) -> typing.Union[str, typing.List[str]]:
        match = GoConfig._InlineMarkerRegex.match(argument)
        if not match:
            return argument

        if match.groups()[0]:
            applyIndex = int(match.groups()[0])

            if applyIndex >= len(self.ApplyLists):
                return argument

            self._ApplyListsUsed[applyIndex] = True
            self._CurrentApplyListIndex = (applyIndex + 1) % len(self.ApplyLists)

            return self.ApplyLists[applyIndex].List
        else:
            applyIndex = self._CurrentApplyListIndex
            self._ApplyListsUsed[applyIndex] = True
            self._CurrentApplyListIndex = (self._CurrentApplyListIndex + 1) % len(self.ApplyLists)

            return self.ApplyLists[applyIndex].List


class ParallelRunner:
    def __init__(self, config: GoConfig):
        self._Configuration = config

        self._MaxParallel = None if self._Configuration.Batched else self._Configuration.ParallelLimit

        self._SubprocessArgs = []
        self._PrintArray = []
        self._PrintArrayLock = threading.Lock()
        self._MainRunnerThread = threading.Thread(target=self._Runner)
        self._PrinterThread = threading.Thread(target=self._Printer)
        self._PrinterThreadStopEvent = False

    def EnqueueRun(self, subprocessArgs: dict):
        self._SubprocessArgs.append(subprocessArgs)

    def Start(self):
        self._Batchify()

        self._MainRunnerThread.start()
        self._PrinterThread.start()
        self._MainRunnerThread.join()

        self._PrinterThreadStopEvent = True
        self._PrinterThread.join()

    def _Batchify(self):
        batchSize = len(self._SubprocessArgs) if not self._Configuration.Batched else self._Configuration.ParallelLimit
        self._SubprocessArgs = list(Utils.Batch(self._SubprocessArgs, batchSize))

    def _Runner(self):
        for batch in self._SubprocessArgs:
            self._RunBatch(batch)

    def _RunBatch(self, batch: typing.List[dict]):
        batchSize = len(batch)
        parallelLimit = batchSize if self._MaxParallel is None else self._MaxParallel
        semaphore = threading.Semaphore(parallelLimit)
        threads = []

        for run in batch:
            semaphore.acquire()

            thread = threading.Thread(target=ParallelRunner._RunInstance,
                                      args=(dict(run), semaphore, self._PrintArray, self._PrintArrayLock))
            threads.append(thread)

            thread.start()

        for thread in threads:
            thread.join()

    @staticmethod
    def _RunInstance(runParameters: dict, doneSemaphore: threading.Semaphore,
                     printList: typing.List, printListLock: threading.Lock):
        if "stdout" in runParameters and runParameters["stdout"] == sys.stdout:
            runParameters["stdout"] = subprocess.PIPE
        # if "stderr" in runParameters and runParameters["stderr"] == sys.stderr:
        #    runParameters["stderr"] = subprocess.PIPE

        printIndex = None
        with printListLock:
            printIndex = len(printList)
            printList.append(None)

        process = subprocess.Popen(**runParameters)

        for line in process.stdout:
            with printListLock:
                printList[printIndex] = line.decode("utf-8").strip()

        with printListLock:
            printList[printIndex] = None

        doneSemaphore.release()

    def _Printer(self):
        time.sleep(0.01)

        while not self._PrinterThreadStopEvent:
            length = len(self._PrintArray)
            tempArray = []

            for i in range(length):
                if self._PrintArray[i] is not None:
                    tempArray.append((i, self._PrintArray[i]))

            os.system("cls")
            for (i, output) in tempArray:
                print("[{0:3d}]  {1}".format(i + 1, output))

            print("{0:3d} / {1:3d} done".format(sum(1 if x is None else 0 for x in self._PrintArray),
                                                sum(len(x) for x in self._SubprocessArgs)))

            time.sleep(0.25)


def FindMatchesAndAlternatives(config: GoConfig, target: str) -> typing.Tuple[typing.List[str], typing.List[str]]:
    if os.path.abspath(target).lower() == target.lower():
        return ([target], [])

    allFiles = config.FetchFiles()
    similarities = []

    for file in allFiles:
        if config.DirectoryFilter:
            (directory, _) = os.path.split(file)
            directory = directory.lower()

            if config.DirectoryFilter.lower() not in directory:
                continue

        similarities.append((file, Utils.ComparePathAndFile(file, target, config.RegexTargetMatch)))

    exactMatches = [x[0] for x in similarities if x[1] == 1.0]

    fuzzyMatches = [x for x in similarities if x[1] >= 0.7 and x[1] < 1.0]
    fuzzyMatches = sorted(fuzzyMatches, key=lambda x: x[1], reverse=True)
    fuzzyMatches = fuzzyMatches[:5]
    fuzzyMatches = [x[0] for x in fuzzyMatches]

    return (exactMatches, fuzzyMatches)


def GetDesiredMatchOrExit(config: GoConfig, target: str) -> str:
    (exactMatches, fuzzyMatches) = FindMatchesAndAlternatives(config, target)

    if len(exactMatches) == 0:
        print(">>>no matches found for \"{0}\"!".format(target))

        if len(fuzzyMatches) > 0:
            print(">>>did you mean:")

            for fuzzyMatch in fuzzyMatches:
                (directory, filename) = os.path.split(fuzzyMatch)
                print(">>>    {0:24s} in {1}".format(filename, directory))

        exit()

    if len(exactMatches) > 1 and config.NthMatch is None:
        print(">>>multiple matches found!")

        for i in range(len(exactMatches)):
            (directory, filename) = os.path.split(exactMatches[i])
            print(">>>[{0:2d}]    {1:24s} in {2}".format(i, filename, directory))

        exit()

    if len(exactMatches) > 1 and config.NthMatch is not None:
        if config.NthMatch >= len(exactMatches):
            print(">>>nth match index out of range!")
            exit()

        return exactMatches[config.NthMatch]

    return exactMatches[0]


def Run(config: GoConfig, target: str, targetArguments: typing.List[typing.List[str]]):
    runs = 1
    if config.RepeatCount is not None and len(targetArguments) == 0:
        runs = config.RepeatCount
    elif len(targetArguments) != 0:
        runs = len(targetArguments[0])

    if runs > 50 and not config.SuppressPrompts:
        print(">>>{0} lines present at source. continue? (Y/n)".format(runs))
        answer = input()

        if len(answer) > 0 and answer[0] != 'y':
            exit()

    target = GetDesiredMatchOrExit(config, target)
    parallelRunner = ParallelRunner(config) if config.Parallel else None

    print(">>>running: {0}".format(target))
    sys.stdout.flush()

    for run in range(runs):
        arguments = [y for x in targetArguments for y in x[run:run + 1]]

        if config.EchoTarget:
            print([target] + arguments)
        if config.DryRun:
            continue

        directory = os.path.split(target)[0] if config.ChangeWorkingDirectory else None
        subprocessArgs = {"args": [target] + arguments, "shell": True, "cwd": directory,
                          "stdin": sys.stdin, "stdout": sys.stdout, "stderr": sys.stderr}

        if config.Parallel:
            parallelRunner.EnqueueRun(subprocessArgs)
        else:
            runMethod = subprocess.run if config.WaitForExit else subprocess.Popen
            runMethod(**subprocessArgs)

    if config.Parallel and not config.DryRun:
        parallelRunner.Start()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        PrintHelp()
        exit()

    Configuration = GoConfig()

    i = 1
    while i < len(sys.argv):
        if not Configuration.TryParseArgument(sys.argv[i]):
            break
        i += 1

    if i == len(sys.argv):
        PrintHelp()
        exit()

    if not Configuration.Validate():
        exit()

    target = sys.argv[i]
    targetArguments = sys.argv[i + 1:]
    targetArguments = Configuration.ProcessApplyArguments(targetArguments)

    Run(Configuration, target, targetArguments)
