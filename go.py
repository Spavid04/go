# VERSION 98    REV 21.09.23.03

import ctypes
import difflib
import fnmatch
import itertools
import json
import os
import pickle
# import psutil # lazily imported
import re
import subprocess
import tempfile
import threading
import time
import typing
import shlex
import sys
import unicodedata
import urllib.request


QUIET_LEVEL = 0
def can_print(level: int) -> bool:
    return level >= QUIET_LEVEL

def Cprint(*args, level: int = 0, **kwargs):
    if not can_print(level):
        return

    print(*args, **kwargs)
def Cprint_gen(level: int) -> typing.Callable:
    return lambda *args, **kwargs: Cprint(*args, level=level, **kwargs)


def PrintHelp():
    if not can_print(2):
        return
    
    print("The main use of this script is to find an executable and run it easily.")
    print("go [/go argument 1] [/go argument 2] ... <target> [target args] ...")
    print("Run with /examples to print some usage examples.")
    print()
    print("By default, go only searches non-recursively in the current directory and %PATH% variable.")
    print("Specifying an absolute path as a target will always run that target, regardless of it being indexed or not.")
    print("Config files (default: go.config) can be used to specify \"TargetedExtensions\", \"TargetedDirectories\" and \"IgnoredDirectories\".")
    print("Config files are json files.")
    print("Added directories are searched recursively.")
    print("Empty go.config example: {\"TargetedExtensions\":[],\"TargetedDirectories\":[],\"IgnoredDirectories\":[]}\"")
    print("Optional config keys:")
    print("  AlwaysYes [bool]: always set /yes.")
    print("  AlwaysQuiet [bool]: always set /quiet")
    print("  AlwaysFirst [bool]: automatically pick the first of multiple matches")
    print("  AlwaysCache [bool]: always use the path cache by default")
    print("  NoFuzzyMatch [bool]: always set /nofuzzy")
    print("You can also create a \".gofilter\" file listing names with UNIX-like wildcards,")
    print("  and go will ignore matching files/directories recursively. Prepend + or - to the name to explicitly specify")
    print("  whether to include or ignore matches.")
    print()
    print("Avaliable go arguments:")
    print()
    print("/config-XXXX  : Uses the specified config file.")
    print()
    print("/ext[+-]XXXX  : Adds or removes the extension to the executable extensions list.")
    print("/dir[+-]XXXX  : Adds or removes the directory to the searched directories list (recursive).")
    print("/ign[+-]XXXX  : Adds or removes the directory to the ignored directories list (recursive).")
    print("/executables  : Toggle inclusion of files that are marked as executables, regardless of extension.")
    print("                By default, Windows excludes them, and UNIX includes them.")
    print("Any of the previous commands will temporarily disable the path cache.")
    print()
    print("/regex        : Matches the files by regex instead of filenames.")
    print("/wild         : Matches the files by UNIX-like wildcards instead of filenames.")
    print("/in[+-]XXXX   : Add a path substring filter to choose ambiguous matches (in+ or (not) in-).")
    print("/nth-XX       : Runs the nth file found. (specified by the 0-indexed XX suffix)")
    print()
    print("/cache[+-]    : Instruct go whether to use the path cache. By default, it is not used.")
    print("                Will be created if not already existing, or if more than one week old.")
    print("                Speeds up target lookup if you have a wide path.")
    print("                Also see config option \"AlwaysCache\".")
    print("/refresh      : Manually refresh the path cache.")
    print("/nofuzzy      : Disable fuzzy matching, speeding up target search.")
    print()
    print("/quiet        : Supresses any messages (but not exceptions) from this script. /yes is implied.")
    print("                Repeat the \"q\" to suppress more messages (eg. /qqquiet). Maximum is 3 q's.")
    print("/yes          : Suppress inputs by answering \"yes\" (or the equivalent).")
    print("/echo         : Echoes the command to be run, including arguments, before running it.")
    print("/dry          : Does not actually run the target executable.")
    print("/list         : Alias for /echo + /dry.")
    print()
    print("/cd           : Runs the target in the target's directory, instead of the current one.")
    print("                Append a -[path] to execute in the specified directory")
    print("/elevate      : Requests elevation before running the target. Might break stdin/out/err pipes.")
    print("/fork         : Does not wait for the started process to end.")
    print("/detach       : Detaches child processes, but can create unwanted windows. Usually used with /fork.")
    print("/waitfor-XX   : Delays execution until after the specified process (PID) has stopped running. Can be repeated.")
    print("/parallel     : Starts all instances, and then waits for all. Valid only with /*apply argument.")
    print("/limit-XX     : Limits parallel runs to have at most XX targets running at once.")
    print("/batch-XX     : Batches parallel runs in sizes of XX. Valid only after /parallel.")
    print("/asscript     : Passes all commands to the default shell interpreter, as a file. Incompatible with most modifiers.")
    print("                Appending a + after the argument will not disable shell echo. (/asscript+)")
    print("                Overrides the target to be run with the default shell interpreter, and allows for any target.")
    print("/unsafe       : Run the command as a simple string, and don't escape anything if possible.")
    print()
    print("/repeat-XX    : Repeats the execution XX times (before any apply list trimming is done).")
    print("/rollover[+-] : Sets apply parameters to run as many times as possible.")
    print("                + (default) and - control whether to repeat source lists that are smaller, or to pass empty.")
    print("/crossjoin    : Cross-joins all apply lists, resulting in all possible argument combinations.")
    print("/[type]apply  : For every line in the specified source, runs the target with the line added as arguments.")
    print("                If no inline markers (see below) are specified, all arguments are appended to the end.")
    print("                A type must always be specified.")
    print("                Accepts a number of modifiers with +[modifier], before any apply-specific arguments.")
    print("                Apply-specific arguments must always come last: [apply type](\\+[modifier])*(-[arguments])?")
    print("                Types of apply:")
    print("                    C: reads the input text from the clipboard as lines")
    print("                    F: reads the lines of a file, specified with *-path")
    print("                    G: reads the output lines of a go command, specified with *-command")
    print("                    H: fetches lines from the specified URL")
    print("                    I: reads the immediate string as a comma separated list, specified with *-text")
    print("                    P: reads the input lines from stdin until EOF; returns the same arguments if used again")
    print("                    R: generates a range of numbers and accepts 1 to 3 comma-separated parameters (python range(...))")
    print("                Modifiers:")
    print("                    e        shell-escapes the argument")
    print("                    f:fmt    format the string using a standard printf format")
    print("                    fi/f:fmt same as f:fmt modifier, but treats input as ints or floats")
    print("                    fl:sep   flatten the argument list to a single arg and join the elements with the given separator")
    print("                             if none, the argument list gets flattened to multiple arguments, and must be last")
    print("                    i:x      inserts the argument in the command at the specified 0-based index")
    print("                    rm:rgx   filters out arguments that don't match (anywhere) the specified regex")
    print("                    rs:rgx   returns the first match using the specified regex, for every argument")
    print("                    rms:rgx  equivalent to rm:rgx followed by a rs:rgx")
    print("                    ss:x:y:z extracts a substring from the argument with a python-like indexer expression")
    print("                Inline (inside command arguments) markers:")
    print("                    Syntax: %%[index of apply source; negatives allowed]%%")
    print("                    Specifies where to append the apply lists. Can use the same list more than one time.")
    print("                    Replacement is also done in quoted or complex arguments.")
    print("                    If a number is specified, it applies that list, otherwise it uses the next unused one.")


def PrintExamples():
    if not can_print(2):
        return
    
    print("Run a program:")
    print("    go calc")
    print()
    print("Run a specific program, regardless of it being found or not:")
    print("    go C:\\NotInPath\\ayy.exe")
    print()
    print("Run a program in its directory:")
    print("    go /cd cmd /c dir /b")
    print()
    print("Temporarily add an extension to the allowed list, and run a program with it:")
    print("    go /ext+\"bat\" batchfile")
    print()
    print("Fetch all urls listed in a file, with wget:")
    print("    go /fapply-\"urls.txt\" wget")
    print()
    print("Use a go subcommand as an apply argument:")
    print("    go /gapply-\"cmd /c dir\" cmd /c echo")
    print()
    print("Explicitly set apply argument position with inline markers:")
    print("    go /iapply-\"3,4\" /iapply-\"1,2\" cmd /c echo %%1%% %%0%%")
    print()
    print("Generate all integers between 0 and 100, and format them as a 0 padded 3 digit number:")
    print("    go /rapply+[fi:%03d]-1,100 cmd /c echo")
    print()
    print("Print last 4 characters of all files in the current directory, read from stdin:")
    print("    dir /b | go /papply+[ss:-4:] cmd /c echo")
    print()
    print("Print only the extensions of all files in the current directory, read from stdin; not using [^.]+ due to parsing issues:")
    print("    dir /b | go /papply+[rs:\\..+?$] cmd /c echo")
    print()
    print("Concatenate files using cmd's copy and go's format+flatten:")
    print("    dir /b *.bin | go /asscript /papply+[f:\\\"%s\\\"]+[fl:+] copy /b %%%% out.bin")


class Utils(object):
    @staticmethod
    def GetScriptDir() -> str:
        scriptPath = __file__
        try:
            scriptPath = os.readlink(scriptPath)
        except:
            pass

        scriptDir = os.path.split(scriptPath)[0]
        return scriptDir

    @staticmethod
    def ParseDirectoriesForFiles(directories: typing.List[str], extensions: typing.List[str],
                                 recursive: bool, includeModX: bool,
                                 ignoredDirectories: typing.Optional[typing.List[str]] = None) -> \
            typing.List[typing.Tuple[str, str]]:
        matches = []
        matchingPaths = set()

        directoriesQueue = list(directories)
        while directoriesQueue:
            targetedDirectory = directoriesQueue.pop(0)

            for (root, dirs, files) in os.walk(targetedDirectory, topdown=True):
                if ".gofilter" in files:
                    files.remove(".gofilter")

                    with open(os.path.join(root, ".gofilter"), "r") as f:
                        gofilterFilters = f.read().splitlines()

                    gofilterIgnores = []
                    gofilterIncludes = []
                    for filter in gofilterFilters:
                        if filter[0] == "+":
                            fullpath = os.path.join(root, os.path.normcase(filter[1:]))
                            if os.path.isdir(fullpath):
                                directoriesQueue.append(fullpath)
                            else:
                                gofilterIncludes.append(filter[1:])
                        elif filter[0] == "-":
                            gofilterIgnores.append(filter[1:])
                        else:
                            gofilterIgnores.append(filter)

                    dirs_copy = list(dirs)
                    for dir in dirs_copy:
                        if any(fnmatch.fnmatch(dir, x) for x in gofilterIgnores) \
                                and not any(fnmatch.fnmatch(dir, x) for x in gofilterIncludes):
                            dirs.remove(dir)
                    files_copy = list(files)
                    for file in files_copy:
                        if any(fnmatch.fnmatch(file, x) for x in gofilterIgnores) \
                                and not any(fnmatch.fnmatch(file, x) for x in gofilterIncludes):
                            files.remove(file)

                if recursive and ignoredDirectories:
                    dirs_copy = list(dirs)
                    for dir in dirs_copy:
                        abspath = os.path.abspath(os.path.join(root, dir))
                        if any(os.path.samefile(abspath, x) for x in ignoredDirectories):
                            dirs.remove(dir)

                for file in files:
                    fullpath = os.path.join(root, file)
                    canAdd = False
                    if includeModX:
                        if os.path.isfile(fullpath) and os.access(fullpath, os.X_OK):
                            canAdd = True
                    if not canAdd:
                        (_, extension) = os.path.splitext(file)
                        extension = extension.lower()
                        canAdd = extension in extensions

                    if canAdd:
                        abspath = os.path.abspath(fullpath)
                        if abspath in matchingPaths:
                            continue
                        matchingPaths.add(abspath)
                        matches.append((abspath, file))

                if not recursive:
                    break

        return matches

    _Compare_RegexObject = None

    @staticmethod
    def ComparePathAndPattern(file: str, pattern: str, fuzzy: bool, asRegex: bool, asWildcard: bool) \
            -> float:
        if sys.platform == "win32":
            file = file.lower()
        (filename, _) = os.path.splitext(file)

        if not fuzzy:
            if sys.platform == "win32":
                pattern = pattern.lower()

            return int(filename == pattern or file == pattern)
        elif asRegex:
            if Utils._Compare_RegexObject is None:
                Utils._Compare_RegexObject = re.compile(pattern, re.I)

            if Utils._Compare_RegexObject.match(filename) or Utils._Compare_RegexObject.match(file):
                return 1
            else:
                return 0
        elif asWildcard:
            if sys.platform == "win32":
                pattern = pattern.lower()

            return int(fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(file, pattern))
        else:
            if sys.platform == "win32":
                pattern = pattern.lower()

            return max(difflib.SequenceMatcher(None, filename, pattern).ratio(),
                       difflib.SequenceMatcher(None, file, pattern).ratio())

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

    SAVED_STDIN = []

    @staticmethod
    def ReadStdin() -> typing.List[str]:
        if Utils.SAVED_STDIN:
            return list(Utils.SAVED_STDIN)

        while True:
            try:
                line = input()
            except:
                break

            if not line:
                continue

            Utils.SAVED_STDIN.append(line)

        return list(Utils.SAVED_STDIN)

    @staticmethod
    def ReadAllLines(file: str) -> typing.List[str]:
        with open(file, "r", encoding="utf-8") as f:
            return [x.rstrip("\r\n") for x in f.readlines()]

    @staticmethod
    def CaptureOutput(command: str) -> typing.List[str]:
        lines = []

        process = subprocess.Popen("go " + command, shell=True, stdout=subprocess.PIPE)
        for line in process.stdout:
            lines.append(line.rstrip().decode("utf-8"))

        return lines

    @staticmethod
    def StreamOutput(process: subprocess.Popen) -> typing.Generator[bytes, None, None]:
        stdout = process.stdout
        stderr = process.stderr

        newLineSemaphore = threading.Semaphore(0)

        stdoutData = []
        stdoutLock = threading.Lock()

        stderrData = []
        stderrLock = threading.Lock()

        stdoutThread = threading.Thread(target=Utils._StreamOutput_Helper, args=(stdout, newLineSemaphore,
                                                                                 stdoutData, stdoutLock))
        stderrThread = threading.Thread(target=Utils._StreamOutput_Helper, args=(stderr, newLineSemaphore,
                                                                                 stderrData, stderrLock))

        stdoutThread.start()
        stderrThread.start()

        while True:
            newLineSemaphore.acquire()

            source = None
            lock = None

            if len(stdoutData) > 0:
                source = stdoutData
                lock = stdoutLock
            elif len(stderrData) > 0:
                source = stderrData
                lock = stderrLock
            else:
                newLineSemaphore.acquire()
                if not stdoutThread.is_alive() and not stderrThread.is_alive():
                    break

            with lock:
                yield source.pop(0)

    @staticmethod
    def _StreamOutput_Helper(stream: typing.IO, eventSemaphore: threading.Semaphore,
                             outList: typing.List[bytes], outListLock: threading.Lock):
        for line in stream:
            with outListLock:
                outList.append(line)

            eventSemaphore.release()

        eventSemaphore.release()

    @staticmethod
    def RemoveControlCharacters(s):
        return "".join(ch if unicodedata.category(ch)[0] != "C" else " " for ch in s)

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

    @staticmethod
    def CreateScriptFile(list: typing.List[typing.List[str]], echoOff: bool) -> str:
        if sys.platform == "win32":
            echo = "@echo off"
            suffix = ".bat"
            selfDelete = "(goto) 2>nul & del \"%~f0\""
        else:
            echo = "set echo off" #does this even work
            suffix = ".sh"
            selfDelete = "rm -- \"$0\""

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=suffix, delete=False, newline=None) as f:
            if echoOff:
                f.write(echo)
                f.write("\n")

            for r in list:
                f.write(" ".join(r))
                f.write("\n")

            f.write(selfDelete)
            f.write("\n")

            script = f.name

        os.chmod(script, 0o755)
        return script

    @staticmethod
    def EscapeForShell(text: str) -> str:
        if sys.platform == "win32":
            if not text or re.search(r"([\"\s])", text):
                text = "\"" + text.replace("\"", r"\"") + "\""

            meta_chars = "()%!^\"<>&|"
            meta_re = re.compile("(" + "|".join(re.escape(char) for char in list(meta_chars)) + ")")
            meta_map = {char: "^%s" % char for char in meta_chars}

            def escape_meta_chars(m):
                char = m.group(1)
                return meta_map[char]

            return meta_re.sub(escape_meta_chars, text)
        else:
            return shlex.quote(text)

    @staticmethod
    def WaitForProcesses(pids: typing.List[int]):
        if "psutil" not in sys.modules:
            try:
                import psutil
            except ModuleNotFoundError:
                Cprint(">>>psutil module not found; /waitfor will not work!", level=2)
                return

        exited = [False]*len(pids)
        Cprint("Waiting for: " + ", ".join(str(x) for x in pids))

        while not all(exited):
            for i in range(len(pids)):
                if exited[i]:
                    continue

                exists = psutil.pid_exists(pids[i])
                if not exists:
                    exited[i] = True
                    Cprint(str(pids[i]) + " exited")
            time.sleep(0.1)

    @staticmethod
    def GetTextFromUrl(url: str) -> typing.List[str]:
        data = urllib.request.urlopen(url)
        lines = []

        for line in data:
            lines.append(line.decode("utf-8"))

        return lines


class GoConfig:
    _QuietRegex = re.compile("^/(q+)uiet$", re.I)
    _ApplyRegex = re.compile("^/([cfghipr])apply(.*)$", re.I)

    def __init__(self):
        self.ConfigFile = "go.config"

        self.TargetedExtensions = [".exe", ".cmd", ".bat", ".py"]
        self.TargetedDirectories = []
        self.IgnoredDirectories = []
        self.Executables = False if sys.platform == "win32" else True

        self.UsePathCache = False
        self.RefreshPathCache = False
        self.FuzzyMatch = True

        self.RegexTargetMatch = False
        self.WildcardTargetMatch = False
        self.DirectoryFilter = []  # type: typing.List[typing.Tuple[bool, str]]
        self.NthMatch = None
        self.FirstMatchFromConfig = False

        self.QuietGo = 0
        self.EchoTarget = False
        self.DryRun = False
        self.SuppressPrompts = False

        self.ChangeWorkingDirectory = False
        self.WorkingDirectory = None
        self.WaitForExit = True
        self.Detach = False
        self.WaitFor = []  # type: typing.List[int]
        self.Parallel = False
        self.Batched = False
        self.ParallelLimit = None
        self.AsShellScript = False
        self.EchoOff = True
        self.Unsafe = False

        self.ApplyLists = []  # type: typing.List[GoConfig.ApplyElement]
        self.Rollover = False
        self.RolloverZero = False
        self.RepeatCount = None
        self.CrossJoin = False

        self.ReloadConfig(False)

    def ReloadConfig(self, overwriteSettings: bool):
        path = self.ConfigFile

        if os.path.abspath(path).lower() != path.lower():
            scriptDir = Utils.GetScriptDir()
            path = os.path.join(scriptDir, path)

        targetedExtensions = []
        targetedDirectories = []

        try:
            with open(path, "r") as f:
                config = json.load(f)

                targetedExtensions = config["TargetedExtensions"]
                targetedDirectories = config["TargetedDirectories"]
                ignoredDirectories = config["IgnoredDirectories"]
        except:
            Cprint(">>>config file invalid or missing", level=2)
            return

        if overwriteSettings:
            self.TargetedExtensions = targetedExtensions
            self.TargetedDirectories = targetedDirectories
            self.IgnoredDirectories = ignoredDirectories
        else:
            self.TargetedExtensions.extend(targetedExtensions)
            self.TargetedDirectories.extend(targetedDirectories)
            self.IgnoredDirectories.extend(ignoredDirectories)

        if "AlwaysYes" in config and config["AlwaysYes"]:
            self.TryParseArgument("/yes")
        if "AlwaysQuiet" in config and config["AlwaysQuiet"]:
            self.TryParseArgument("/yes")
        if "AlwaysFirst" in config and config["AlwaysFirst"]:
            self.FirstMatchFromConfig = True
        if "AlwaysCache" in config and config["AlwaysCache"]:
            self.UsePathCache = True
        if "NoFuzzyMatch" in config and config["NoFuzzyMatch"]:
            self.FuzzyMatch = False

    class ApplyElement:
        def __init__(self,
                     sourceType: str,
                     modifiers: typing.Optional[typing.List[typing.Tuple[str, typing.Any]]] = None,
                     source: typing.Optional[str] = None):
            self.SourceType = sourceType
            self.Modifiers = modifiers if modifiers is not None else []
            self.Source = source

            self.List = None

    def TryParseArgument(self, argument: str) -> bool:
        lower = argument.lower()

        if lower == "/examples":
            PrintExamples()
            exit(0)

        elif lower.startswith("/config-"):
            path = argument[8:]
            self.ConfigFile = path
            self.ReloadConfig(True)
        elif lower.startswith("/dir"):
            action = lower[4]
            path = os.path.abspath(lower[5:])

            if action == "-":
                if path in self.TargetedDirectories:
                    self.TargetedDirectories.remove(path)
            else:
                if path not in self.TargetedDirectories:
                    self.TargetedDirectories.append(path)
            self.UsePathCache = False
        elif lower.startswith("/ign"):
            action = lower[4]
            path = os.path.abspath(lower[5:])

            if action == "-":
                if path in self.IgnoredDirectories:
                    self.IgnoredDirectories.remove(path)
            else:
                if path not in self.IgnoredDirectories:
                    self.IgnoredDirectories.append(path)
            self.UsePathCache = False
        elif lower.startswith("/ext"):
            action = lower[4]
            extension = lower[5:]

            if action == "-":
                if extension in self.TargetedExtensions:
                    self.TargetedExtensions.remove(extension)
            else:
                if extension not in self.TargetedExtensions:
                    self.TargetedExtensions.append(extension)
            self.UsePathCache = False
        elif lower == "/executables":
            self.Executables = not self.Executables
            self.UsePathCache = False

        elif lower.startswith("/cache"):
            if len(lower) >= 7:
                value = lower[6]
                if value == "+":
                    self.UsePathCache = True
                elif value == "-":
                    self.UsePathCache = False
            else:
                self.UsePathCache = True
        elif lower == "/refresh":
            self.RefreshPathCache = True
        elif lower == "/nofuzzy":
            self.FuzzyMatch = False

        elif lower == "/regex":
            self.RegexTargetMatch = True
        elif lower == "/wild":
            self.WildcardTargetMatch = True
        elif lower.startswith("/in"):
            mode = True if lower[3] == "+" else False
            substring = argument[4:]

            self.DirectoryFilter.append((mode, substring))
        elif lower.startswith("/nth"):
            self.NthMatch = 0

            nthAsString = lower[5:]
            if len(nthAsString) > 0:
                self.NthMatch = int(nthAsString)

        elif GoConfig._QuietRegex.match(argument):
            m = GoConfig._QuietRegex.match(argument)
            count = len(m.group(1))

            global QUIET_LEVEL
            QUIET_LEVEL += count
            self.QuietGo += count
            self.TryParseArgument("/yes")
        elif lower == "/list":
            self.TryParseArgument("/echo")
            self.TryParseArgument("/dry")
        elif lower == "/echo":
            self.EchoTarget = True
        elif lower == "/dry":
            self.DryRun = True
        elif lower == "/yes":
            self.SuppressPrompts = True

        elif lower == "/elevate":
            Utils.EnsureAdmin()
        elif lower.startswith("/cd"):
            self.ChangeWorkingDirectory = True
            wd = argument[4:]
            if wd:
                self.WorkingDirectory = wd
        elif lower == "/fork":
            self.WaitForExit = False
        elif lower == "/detach":
            self.Detach = True
        elif lower.startswith("/waitfor-"):
            self.WaitFor.append(int(lower[9:]))
        elif lower == "/parallel":
            self.Parallel = True
        elif lower == "/batch":
            self.Batched = True
        elif lower.startswith("/limit-"):
            self.ParallelLimit = int(lower[7:])
        elif lower.startswith("/asscript"):
            self.AsShellScript = True
            if "+" in lower:
                self.EchoOff = False
        elif lower == "/unsafe":
            self.Unsafe = True

        elif GoConfig._ApplyRegex.match(lower):
            groups = GoConfig._ApplyRegex.match(argument).groups()
            type = groups[0]
            argsstr = groups[1]
            argregex = re.compile("\\+\\[(.+?)\\](?=$|-|\\+)|-(.+)$", re.I)

            modifiers = []
            applyArgument = None

            for match in argregex.finditer(argsstr):
                if match.group(1):
                    modifierText = match.group(1)
                    if m := re.match("i:(\\d+)", modifierText, re.I):
                        modifiers.append(("i", int(m.group(1))))
                    elif modifierText == "e":
                        modifiers.append(("e", None))
                    elif m := re.match("(f[if]?):(.+)", modifierText, re.I):
                        modifiers.append((m.group(1), m.group(2)))
                    elif m := re.match("fl:?(.+)?", modifierText, re.I):
                        separator = None if (m.group(1) is None and ":" not in modifierText) else m.group(1)
                        modifiers.append(("fl", separator))
                    elif m := re.match("ss:(-?\\d+)?(:)?(-?\\d+)?(:)?(-?\\d+)?", modifierText, re.I):
                        x = m.group(1) or ""
                        y = m.group(3) or ""
                        z = m.group(5) or ""
                        colons = bool(m.group(2)) + bool(m.group(4))

                        expression = x
                        if colons >= 1:
                            expression += ":" + y
                        if colons == 2:
                            expression += ":" + z

                        func = eval("lambda x : x[" + expression + "]")
                        modifiers.append(("ss", func))
                    elif m := re.match("(r[ms]+):(.+)", modifierText, re.I):
                        if len(m.group(1)) == 2:
                            modifiers.append((m.group(1), m.group(2)))
                        elif m.group(1) == "rms":
                            modifiers.append(("rm", m.group(2)))
                            modifiers.append(("rs", m.group(2)))

                elif match.group(2):
                    applyArgument = match.group(2)

            self.ApplyLists.append(GoConfig.ApplyElement(type, modifiers, applyArgument))
        elif lower.startswith("/rollover"):
            self.Rollover = True
            if "-" in lower:
                self.RolloverZero = True
        elif lower.startswith("/repeat-"):
            self.RepeatCount = int(lower[8:])
        elif lower == "/crossjoin":
            self.CrossJoin = True

        else:
            return False

        return True

    def Validate(self) -> bool:
        if self.Parallel and not self.WaitForExit:
            Cprint(">>>/fork doesn't do anything with /parallel", level=1)

        if self.Batched and not self.ParallelLimit:
            Cprint(">>>/batch requires /limit to be specified", level=2)
            return False

        if self.AsShellScript and self.Parallel:
            Cprint(">>>/asscript cannot be used with /parallel", level=1)

        if self.CrossJoin and (self.RepeatCount or self.Rollover):
            Cprint(">>>/crossjoin cannot be used either /rollover or /repeat", level=2)
            return False

        if self.RegexTargetMatch and self.WildcardTargetMatch:
            Cprint(">>>/regex and /wild cannot be used together", level=2)
            return False

        return True

    def ProcessApplyArguments(self, targetArguments: typing.List[str]) -> typing.List[typing.List[str]]:
        if len(self.ApplyLists) == 0:
            repeat = 1 if self.RepeatCount is None else self.RepeatCount
            return [[x] * repeat for x in targetArguments]

        # region generate lists

        for applyArgument in self.ApplyLists:
            if applyArgument.SourceType == "c":
                applyArgument.List = [x for x in Utils.GetClipboardText().split("\r\n") if len(x) > 0]
            elif applyArgument.SourceType == "f":
                applyArgument.List = Utils.ReadAllLines(applyArgument.Source)
            elif applyArgument.SourceType == "g":
                applyArgument.List = Utils.CaptureOutput(applyArgument.Source)
            elif applyArgument.SourceType == "h":
                applyArgument.List = Utils.GetTextFromUrl(applyArgument.Source)
            elif applyArgument.SourceType == "i":
                applyArgument.List = applyArgument.Source.split(",")
            elif applyArgument.SourceType == "p":
                applyArgument.List = Utils.ReadStdin()
            elif applyArgument.SourceType == "r":
                rangeArgumentsRegex = re.compile("-?\\d+(,-?\\d+){0,2}", re.I)
                if rangeArgumentsRegex.match(applyArgument.Source):
                    applyArgument.List = [str(x) for x in eval("range(" + applyArgument.Source + ")")]

        # endregion

        # region process modifiers

        for applyArgument in self.ApplyLists:
            for (modifierType, modifierArgument) in applyArgument.Modifiers:
                if modifierType == "e":
                    applyArgument.List = [Utils.EscapeForShell(x) for x in applyArgument.List]
                elif modifierType in {"f", "fi", "ff"}:
                    convertFunc = lambda x: x
                    if modifierType == "fi":
                        convertFunc = lambda x: int(x)
                    elif modifierType == "ff":
                        convertFunc = lambda x: float(x)

                    for i in range(len(applyArgument.List)):
                        applyArgument.List[i] = modifierArgument % convertFunc(applyArgument.List[i])
                elif modifierType == "fl":
                    if modifierArgument is not None:
                        applyArgument.List = [modifierArgument.join(applyArgument.List)]
                    else:
                        applyArgument.List = [applyArgument.List]
                elif modifierType == "ss":
                    applyArgument.List = [modifierArgument(x) for x in applyArgument.List]
                elif modifierType == "rm":
                    regex = re.compile(modifierArgument, re.I)
                    applyArgument.List = [x for x in applyArgument.List if regex.search(x)]
                elif modifierType == "rs":
                    regex = re.compile(modifierArgument, re.I)
                    for i in range(len(applyArgument.List)):
                        match = regex.search(applyArgument.List[i])
                        if match:
                            applyArgument.List[i] = match.group(0)
                        else:
                            applyArgument.List[i] = ""

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

                if self.RolloverZero:
                    applyArgument.List += [""] * (maxOriginalLength - originalLength)
                else:
                    while len(applyArgument.List) < maxOriginalLength:
                        applyArgument.List.extend(applyArgument.List[:originalLength])

        if self.CrossJoin:
            crossjoined = itertools.product(*[x.List for x in self.ApplyLists])
            crossjoined = list(map(list, zip(*crossjoined))) # transpose

            for i in range(len(self.ApplyLists)):
                self.ApplyLists[i].List = crossjoined[i]

        minLength = min(len(x.List) for x in self.ApplyLists)

        for applyArgument in self.ApplyLists:
            if len(applyArgument.List) > minLength:
                applyArgument.List = applyArgument.List[:minLength]

        # endregion

        newArguments = []

        # region process indexers and inline markers

        self._ApplyListsUsed = [False] * len(self.ApplyLists)
        self._CurrentApplyListIndex = 0

        for targetArgument in targetArguments:
            newArgument = self._ProcessInlineMarker(targetArgument)
            newArguments.append(newArgument)

        for i in range(len(self.ApplyLists)):
            applyArgument = self.ApplyLists[i]
            for indexer in (x for x in applyArgument.Modifiers if x[0] == "i"):
                newArguments.insert(indexer[1], applyArgument.List)
                self._ApplyListsUsed[i] = True

        applyLength = 1 if len(self.ApplyLists) == 0 else len(self.ApplyLists[0].List)

        for i in range(len(newArguments)):
            if isinstance(newArguments[i], str):
                newArguments[i] = [newArguments[i]] * applyLength

        for i in range(len(self.ApplyLists)):
            if not self._ApplyListsUsed[i]:
                newArguments.append(self.ApplyLists[i].List)

        # endregion

        # region flatten expanded lists

        i = 0
        while i < len(newArguments):
            arg = newArguments[i]

            if isinstance(arg[0], list):
                newArguments.pop(i)
                for j in range(len(arg[0])):
                    flattened = []
                    for k in arg:
                        flattened.append(k[j])
                    newArguments.insert(i, flattened)
                    i += 1
            i += 1

        # endregion

        return newArguments

    _InlineMarkerRegex = re.compile(r"%%(-?\d*)%%", re.I)

    def _ProcessInlineMarker(self, argument: str) -> typing.Union[str, typing.List[str]]:
        matches = list(GoConfig._InlineMarkerRegex.finditer(argument))
        if not matches:
            return argument

        processed = []
        for match in matches:
            if match.group(1):
                applyIndex = int(match.group(1))
                if applyIndex < -len(self.ApplyLists) or applyIndex >= len(self.ApplyLists):
                    return argument
            else:
                applyIndex = self._CurrentApplyListIndex

            sourceList = list(self.ApplyLists[applyIndex].List)
            self._ApplyListsUsed[applyIndex] = True
            self._CurrentApplyListIndex = (applyIndex + 1) % len(self.ApplyLists)

            if not processed:
                processed = [argument] * len(sourceList)

            markerString = match.group(0)
            for i in range(len(processed)):
                processed[i] = processed[i].replace(markerString, sourceList[i])
        return processed


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
        if "stderr" in runParameters and runParameters["stderr"] == sys.stderr:
            runParameters["stderr"] = subprocess.PIPE

        printIndex = None
        with printListLock:
            printIndex = len(printList)
            printList.append(None)

        process = subprocess.Popen(**runParameters)

        for line in Utils.StreamOutput(process):
            with printListLock:
                printList[printIndex] = line.decode("utf-8").strip()

        with printListLock:
            printList[printIndex] = None

        doneSemaphore.release()

    def _Printer(self):
        if not can_print(1):
            return

        time.sleep(0.01)

        while not self._PrinterThreadStopEvent:
            length = len(self._PrintArray)
            tempArray = []

            for i in range(length):
                if self._PrintArray[i] is not None:
                    tempArray.append((i, self._PrintArray[i]))

            if sys.platform == "win32":
                os.system("cls")
            else:
                os.system("clear")
            for (i, output) in tempArray:
                print("[{0:3d}]  {1}".format(i + 1, Utils.RemoveControlCharacters(output)))

            print("{0:3d} / {1:3d} done".format(sum(1 if x is None else 0 for x in self._PrintArray),
                                                sum(len(x) for x in self._SubprocessArgs)))

            time.sleep(0.25)


def unique(lst: typing.List[typing.Tuple[str, str]]) -> typing.List[typing.Tuple[str, str]]:
    temp = {}

    for i in range(len(lst)):
        item = lst[i]

        key = (os.path.normcase(item[0]), os.path.normcase(item[1]))
        if key in temp:
            continue

        temp[key] = (i, item)

    asList = list(temp.values())
    asList.sort(key=lambda x: x[0])
    return [x[1] for x in asList]


def FindMatchesAndAlternatives(config: GoConfig, target: str) -> typing.Tuple[typing.List[str], typing.List[str]]:
    if os.path.abspath(target).lower() == target.lower():
        return ([target], [])

    allFiles = []

    scriptDir = Utils.GetScriptDir()
    cachePath = os.path.join(scriptDir, "go.cache")
    overwriteCache = config.RefreshPathCache

    if config.UsePathCache and not config.RefreshPathCache:
        if os.path.isfile(cachePath):
            with open(cachePath, "rb") as f:
                (lastRefresh, cachedPaths) = pickle.load(f)

            if lastRefresh < (time.time() - (60*60*24*7)):
                overwriteCache = True
            else:
                if not config.RefreshPathCache:
                    allFiles.extend(cachedPaths)
        else:
            overwriteCache = True

    if len(allFiles) == 0:
        allFiles.extend(Utils.ParseDirectoriesForFiles(os.environ["PATH"].split(os.pathsep), config.TargetedExtensions, False, config.Executables))
        allFiles.extend(Utils.ParseDirectoriesForFiles([os.getcwd()], config.TargetedExtensions, False, config.Executables))
        allFiles.extend(Utils.ParseDirectoriesForFiles(config.TargetedDirectories, config.TargetedExtensions, True,
                                                       config.Executables, config.IgnoredDirectories))
        allFiles = unique(allFiles)

    if overwriteCache:
        with open(cachePath, "wb") as f:
            pickle.dump((time.time(), allFiles), f)

    similarities = []
    for (path, file) in allFiles:
        passedThrough = True

        for (include, directoryFilter) in config.DirectoryFilter:
            (directory, _) = os.path.split(path)
            directory = directory.lower()

            if (include and directoryFilter.lower() not in directory) or \
                    (not include and directoryFilter.lower() in directory):
                passedThrough = False
                break

        if not passedThrough:
            continue

        similarities.append((path, Utils.ComparePathAndPattern(file, target, config.FuzzyMatch,
                                                               config.RegexTargetMatch, config.WildcardTargetMatch)))

    exactMatches = [x[0] for x in similarities if x[1] == 1.0]

    fuzzyMatches = [x for x in similarities if x[1] >= 0.7 and x[1] < 1.0]
    fuzzyMatches = sorted(fuzzyMatches, key=lambda x: x[1], reverse=True)
    fuzzyMatches = fuzzyMatches[:5]
    fuzzyMatches = [x[0] for x in fuzzyMatches]

    return (exactMatches, fuzzyMatches)


def GetDesiredMatchOrExit(config: GoConfig, target: str) -> str:
    (exactMatches, fuzzyMatches) = FindMatchesAndAlternatives(config, target)

    if len(exactMatches) == 0:
        Cprint(">>>no matches found for \"{0}\"!".format(target), level=2)

        if len(fuzzyMatches) > 0:
            Cprint(">>>did you mean:", level=2)

            for fuzzyMatch in fuzzyMatches:
                (directory, filename) = os.path.split(fuzzyMatch)
                Cprint(">>>    {0:24s} in {1}".format(filename, directory), level=2)

        exit(-1)

    nthMatch = config.NthMatch
    if nthMatch is None and config.FirstMatchFromConfig:
        nthMatch = 0

    if len(exactMatches) > 1 and nthMatch is None:
        Cprint(">>>multiple matches found!", level=2)

        for i in range(len(exactMatches)):
            (directory, filename) = os.path.split(exactMatches[i])
            Cprint(">>> [{0:2d}]\t{1:20s}\tin {2}".format(i, filename, directory), level=2)

        exit(-1)
    if len(exactMatches) > 1 and config.FirstMatchFromConfig and config.NthMatch is None:
        Cprint(">>>autoselected the first of many matches because of config \"AlwaysFirst\"!")

    if len(exactMatches) > 1 and nthMatch is not None:
        if nthMatch >= len(exactMatches):
            Cprint(">>>nth match index out of range!", level=2)
            exit(-1)

        return exactMatches[nthMatch]

    return exactMatches[0]


def Run(config: GoConfig, goTarget: str, targetArguments: typing.List[typing.List[str]]) -> typing.Optional[int]:
    runs = 1
    if config.RepeatCount is not None and len(targetArguments) == 0:
        runs = config.RepeatCount
    elif len(targetArguments) != 0:
        runs = len(targetArguments[0])

    if runs > 50 and not config.SuppressPrompts:
        Cprint(">>>{0} lines present at source. continue? (Y/n)".format(runs), level=2)
        answer = ""
        try:
            answer = input()
        except EOFError:
            Cprint(">>>could not read stdin; use /yes to run", level=2)
            exit(-1)

        if len(answer) > 0 and answer[0] != "y":
            exit(-1)

    if config.AsShellScript:
        if sys.platform == "win32":
            target = GetDesiredMatchOrExit(config, "cmd.exe")
        else:
            target = GetDesiredMatchOrExit(config, "bash")
    else:
        target = GetDesiredMatchOrExit(config, goTarget)
    parallelRunner = ParallelRunner(config) if config.Parallel else None
    runMethod = subprocess.run if config.WaitForExit else subprocess.Popen
    stdin = sys.stdin if config.WaitForExit else subprocess.DEVNULL
    stdout = sys.stdout if config.WaitForExit else subprocess.DEVNULL
    stderr = sys.stderr if config.WaitForExit else subprocess.DEVNULL
    flags = 0
    asscriptArguments = []

    if not config.WaitForExit:
        flags |= subprocess.CREATE_NEW_PROCESS_GROUP
    if config.Detach:
        flags |= subprocess.DETACHED_PROCESS

    if can_print(0):
        print(">>>target: {0}".format(target))
        sys.stdout.flush()

    if config.ChangeWorkingDirectory:
        if config.WorkingDirectory:
            directory = config.WorkingDirectory
        else:
            directory = os.path.split(target)[0]
    else:
        directory = None

    for run in range(runs):
        arguments = [y for x in targetArguments for y in x[run:run + 1]]

        if config.EchoTarget and can_print(1):
            if config.Unsafe:
                print((target if not config.AsShellScript else goTarget) + " " + " ".join(arguments))
            else:
                print(Utils.EscapeForShell(target if not config.AsShellScript else goTarget) + " " +
                      " ".join(Utils.EscapeForShell(x) for x in arguments))
        if config.DryRun:
            continue
        if config.AsShellScript:
            asscriptArguments.append([goTarget] + arguments)
            continue

        if config.Unsafe:
            runArgument = target + " " + " ".join(arguments)
        else:
            runArgument = [target] + arguments

        subprocessArgs = {"args": runArgument, "shell": True, "cwd": directory, "creationflags": flags,
                          "stdin": stdin, "stdout": stdout, "stderr": stderr, "start_new_session": not config.WaitForExit}

        if config.Parallel:
            parallelRunner.EnqueueRun(subprocessArgs)
        else:
            result = runMethod(**subprocessArgs)
            if config.WaitForExit and runs == 1:
                return result.returncode

    if config.DryRun:
        return 0

    if config.Parallel:
        parallelRunner.Start()
    if config.AsShellScript:
        tempscriptPath = Utils.CreateScriptFile(asscriptArguments, config.EchoOff)
        subprocessArgs = {"args": [tempscriptPath], "shell": True, "cwd": directory, "creationflags": flags,
                          "stdin": stdin, "stdout": stdout, "stderr": stderr, "start_new_session": not config.WaitForExit}
        result = runMethod(**subprocessArgs)
        if config.WaitForExit:
            return result.returncode


if __name__ == "__main__":
    if len(sys.argv) == 1:
        PrintHelp()
        exit(0)

    config = GoConfig()

    i = 1
    while i < len(sys.argv):
        if not config.TryParseArgument(sys.argv[i]):
            break
        i += 1

    if i == len(sys.argv):
        PrintHelp()
        exit()

    if not config.Validate():
        exit(-1)

    if config.WaitFor:
        Utils.WaitForProcesses(config.WaitFor)

    target = sys.argv[i]
    targetArguments = sys.argv[i + 1:]
    targetArguments = config.ProcessApplyArguments(targetArguments)

    result = Run(config, target, targetArguments)
    exit(result or 0)
