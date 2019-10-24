import ctypes
import difflib
import os
import re
import subprocess
import typing
import sys


def PrintHelp():
    # todo
    pass


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
                t = input()
            except:
                break

            lines.append(t)

        return lines

    @staticmethod
    def ReadAllLines(file: str) -> typing.List[str]:
        with open(file) as f:
            return f.readlines()

    @staticmethod
    def CaptureOutput(command: str) -> typing.List[str]:
        lines = []

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
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


class GoConfig:
    _ApplyRegex = re.compile("^/([cfgip])apply-?(.*)$", re.I)

    def __init__(self):
        self.ConfigFile = "go.config"
        # todo configurable ^ V
        self.TargetedExtensions = [".exe", ".cmd", ".bat", ".py"]
        self.TargetedDirectories = []

        self.RegexTargetMatch = False
        self.DirectoryFilter = None
        self.NthMatch = None

        self.QuietGo = False  # todo
        self.EchoTarget = False
        self.DryRun = False
        self.SuppressPrompts = False

        self.ChangeWorkingDirectory = False
        self.WaitForExit = True
        self.Parallel = False  # todo
        self.Batched = False
        self.ParallelLimit = None

        self.ApplyLists = []  # type: typing.List[GoConfig.ApplyElement]
        self.Rollover = False
        self.RepeatCount = None

    class ApplyElement:
        def __init__(self, sourceType: str, source: typing.Optional[str] = None):
            self.SourceType = sourceType
            self.Source = source

            self.List = None

    def TryParseArgument(self, argument: str) -> bool:
        lower = argument.lower()

        if lower == "/regex":
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

            if groups[0] == 'c' or groups[0] == 'p':
                self.ApplyLists.append(GoConfig.ApplyElement(groups[0]))
            elif groups[0] == 'f' or groups[0] == 'g' or groups[0] == 'i':
                self.ApplyLists.append(GoConfig.ApplyElement(groups[0], groups[1]))
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
            return []

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
        print(">>>{0} lines present at source. continue? (y/n)")
        answer = input()[0]

        if answer != 'y':
            exit()

    target = GetDesiredMatchOrExit(config, target)

    for run in range(runs):
        arguments = [y for x in targetArguments for y in x[run:run + 1]]

        if config.EchoTarget:
            print([target] + arguments)
        if config.DryRun:
            continue

        directory = os.path.split(target)[0] if config.ChangeWorkingDirectory else None
        runMethod = subprocess.run if config.WaitForExit else subprocess.Popen

        runMethod([target] + arguments, shell=True, cwd=directory, stdin=sys.stdin, stdout=sys.stdout,
                  stderr=sys.stderr)


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
