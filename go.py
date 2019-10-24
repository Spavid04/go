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
    _Clipboard_Userl32 = None

    @staticmethod
    def GetClipboardText() -> str:
        if not Utils._Clipboard_ValuesInitialized:
            Utils._Clipboard_Kernel32 = ctypes.windll.kernel32
            Utils._Clipboard_Kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            Utils._Clipboard_Kernel32.GlobalLock.restype = ctypes.c_void_p
            Utils._Clipboard_Kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            Utils._Clipboard_Userl32 = ctypes.windll.user32
            Utils._Clipboard_Userl32.GetClipboardData.restype = ctypes.c_void_p

            Utils._Clipboard_ValuesInitialized = True

        Utils._Clipboard_Userl32.OpenClipboard(0)
        try:
            if Utils._Clipboard_Userl32.IsClipboardFormatAvailable(1):  # CF_TEXT
                data = Utils._Clipboard_Userl32.GetClipboardData(1)  # CF_TEXT
                data_locked = Utils._Clipboard_Kernel32.GlobalLock(data)
                text = ctypes.c_char_p(data_locked)
                value = text.value
                Utils._Clipboard_Kernel32.GlobalUnlock(data_locked)
                return value
        finally:
            Utils._Clipboard_Userl32.CloseClipboard()

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
    def __init__(self):
        self.ConfigFile = "go.config"

        self.TargetedExtensions = [".exe", ".cmd", ".bat", ".py"]
        self.TargetedDirectories = []

        self.RegexTargetMatch = False
        self.DirectoryFilter = None
        self.NthMatch = None

        self.QuietGo = False
        self.EchoTarget = False
        self.DryRun = False

        self.ChangeWorkingDirectory = False
        self.WaitForExit = True

        self.
        self.Parallel = False

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
            self.QuietGo = True  # todo
        elif lower == "/list":
            self.TryParseArgument("/echo")
            self.TryParseArgument("/dryrun")
        elif lower == "/echo":
            self.EchoTarget = True
        elif lower == "/dryrun":
            self.DryRun = True

        elif lower == "/elevate":
            Utils.EnsureAdmin()
        elif lower == "/cd":
            self.ChangeWorkingDirectory = True
        elif lower == "/nowait":
            self.WaitForExit = False

        elif lower == "/parallel":
            self.Parallel = True

        else:
            return False

        return True

    def Validate(self) -> bool:
        if self.DryRun and not self.EchoTarget:
            print(">>>invalid arguments: /dry requires /echo")
            return False

        if self.Parallel and not self.WaitForExit:
            print(">>>/nowait doesn't do anything with /parallel")

        return True

    def FetchFiles(self) -> typing.List[str]:
        files = []

        files = Utils.ParseDirectoriesForFiles(os.environ["PATH"].split(";"), self.TargetedExtensions, False)

        for file in Utils.ParseDirectoriesForFiles(self.TargetedDirectories, self.TargetedExtensions, True):
            if file not in files:
                files.append(file)

        return files


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


def GetDesiredMatchOrExit(config: GoConfig, target: str, targetArguments: typing.List[str]) -> str:
    (exactMatches, fuzzyMatches) = FindMatchesAndAlternatives(config, target)

    if config.DryRun and config.EchoTarget and len(exactMatches) > 0:
        for exactMatch in exactMatches:
            print([exactMatch] + targetArguments)

        exit()

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


def Run(config: GoConfig, target: str, targetArguments: typing.List[str]):
    target = GetDesiredMatchOrExit(config, target, targetArguments)

    directory = os.path.split(target)[0] if config.ChangeWorkingDirectory else None
    run = subprocess.run if config.WaitForExit else subprocess.Popen

    if config.EchoTarget:
        print([target] + targetArguments)

    run([target] + targetArguments, shell=True, cwd=directory)


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

    target = sys.argv[i]
    targetArguments = sys.argv[i + 1:]

    if not Configuration.Validate():
        exit()

    Run(Configuration, target, targetArguments)
