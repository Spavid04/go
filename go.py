# VERSION 159    REV 25.04.19.02

import ctypes
import difflib
import enum
import fnmatch
import importlib.util
import itertools
import json
import os
import pickle
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import typing
import shlex
import stat
import sys
import unicodedata
import urllib.request

# optional requirements:

try:
    import regex as re
except:
    import re

COLORAMA_AVAILABLE = False
try:
    import colorama
    COLORAMA_AVAILABLE = True
except:
    pass

ILOCK_AVAILABLE = False
try:
    import ilock
    ILOCK_AVAILABLE = True
except:
    pass

PSUTIL_AVAILABLE = False
try:
    sys.stderr = open(os.devnull, "w")
    import psutil
    PSUTIL_AVAILABLE = True
except:
    pass
finally:
    sys.stderr = sys.__stderr__

PYPERCLIP_AVAILABLE = False
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except:
    pass


config: "GoConfig" = None

MAX_QUIET_LEVEL = 3
MAX_VERBOSE_LEVEL = 2
PRINT_LEVEL = 0
def change_level(offset: int):
    global PRINT_LEVEL
    PRINT_LEVEL = offset
def can_print(level: int) -> bool:
    return level >= PRINT_LEVEL
def Cprint(*args, level: int = 0, **kwargs):
    if not can_print(level):
        return
    print(*args, **kwargs)
def Cprint_gen(level: int) -> typing.Callable:
    return lambda *args, **kwargs: Cprint(*args, level=level, **kwargs)


VERSION_REGEX = re.compile(r"^.*?(\d+).+(\d\d\.\d\d\.\d\d\.\d\d).*$")
CURRENT_VERSION = None
def parse_version(line: str) -> (str, str):
    m = VERSION_REGEX.match(line)
    return (m.group(1), m.group(2))
def get_current_version() -> (str, str):
    global CURRENT_VERSION
    if CURRENT_VERSION is None:
        with open(__file__, "r", encoding="utf-8") as f:
            line = f.readline().strip()
        CURRENT_VERSION = parse_version(line)
    return CURRENT_VERSION

def PrintHelp():
    if not can_print(2):
        return

    print("Revision %s    Version Date %s" % get_current_version())
    print()
    print("The main use of this script is to find an executable and run it easily.")
    print("go [/go argument 1] [/go argument 2] ... <target> [target args] ...")
    print("Run with /help to print this help.")
    print("Run with /examples to print some usage examples.")
    print("Run with /modulehelp to print help about external py scripts.")
    print("Homepage: https://github.com/Spavid04/go")
    print()
    print("By default, go only searches non-recursively in the current directory and %PATH% variable.")
    print("Specifying an absolute path as a target will always run that target, regardless of it being indexed or not.")
    print()
    print("All regex operations use the more advanced \"regex\" pypi package, if it is installed.")
    print()
    print("Config files (default: go.config) can be used to specify static options in a JSON format.")
    print("Config keys:")
    print("  TargetedPaths [list[str]]: additional searched paths; recursive if a directory")
    print("  TargetedExtensions [list[str]]: additional extensions considered executable")
    print("  IgnoredPaths [list[str]]: additional ignored paths; recursive if a directory")
    print("  AlwaysYes [bool]: always set /yes.")
    print("  AlwaysQuiet [0-3 or bool]: if bool set /quiet, if int set the level of /quiet")
    print("  AlwaysFirst [bool]: automatically pick the first of multiple matches")
    print("  AlwaysCache [bool]: always use the path cache by default (/cache+)")
    print("  AlwaysShell [bool]: always run the target through the shell (/shell)")
    print("  AutoPapplyPipes [bool]: if stdin is a pipe, automatically prepend a papply argument (/autopipe)")
    print("  AutoSilentPipe [bool]: if stdout is a pipe, silence all output. Additionally, if stdin is a pipe, pass /yes.")
    print("  NoFuzzyMatch [bool]: always set /nofuzzy")
    print("  IncludeHidden [bool]: specify whether to include hidden files and directories")
    print("  CacheInvalidationTime [float]: override the default cache invalidation time with the specified one, in hours")
    print("  DefaultArguments [list[str]]: prepend the given arguments before any command line arguments every go run")
    print()
    print("Environment variables:")
    print("  GO_DEFAULT_ARGUMENTS [str] : a shell-separated list of arguments to prepend to every go instance")
    print()
    print("By creating a \".gofilter\" or \"go.filter\"c file inside a searched directory, listing names with UNIX-like wildcards,")
    print("  go will ignore or include matching files/directories recursively.")
    print("Prepend + or - to the name to explicitly specify whether to include or ignore matches.")
    print("Filters can include files and directories not directly under the current one.")
    print()
    print("Avaliable go arguments:")
    print("All arguments accept a -- prefix instead of /")
    print()
    print("/update       : Check for go.py script update.")
    print("/config-XXXX  : Uses the specified config file.")
    print()
    print("/ext[+-]XXXX  : Adds or removes the extension to the executable extensions list.")
    print("/inc[+-]XXXX  : Adds or removes the path to the searched paths list (recursive if a directory).")
    print("/exc[+-]XXXX  : Adds or removes the path to the ignored paths list (recursive if a directory).")
    print("/executables  : Toggle inclusion of files that are marked as executables, regardless of extension.")
    print("                By default, Windows excludes them, and UNIX includes them.")
    print("/hidden[+-]   : Includes or excludes hidden files and directories. Omitting + or - toggles the setting.")
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
    print("/refresh      : Manually refresh the path cache.")
    print("/nofuzzy      : Disable fuzzy matching, speeding up target search.")
    print("/duplinks     : Include symlinks to executables that were already found.")
    print("/nofilters    : Ignore gofilter files.")
    print()
    print("/quiet        : Supresses any messages (but not exceptions) from this script. /yes is implied.")
    print("                Repeat the \"q\" to suppress more messages (eg. /qqquiet). Maximum is " + str(MAX_QUIET_LEVEL) + " q's.")
    print("/verbose      : Enables verbose messages.")
    print("                Repeat the \"v\" to enable more messages (eg. /vverbose). Maximum is " + str(MAX_VERBOSE_LEVEL) + " v's.")
    print("/qmax         : Sets the maximum quiet level.")
    print("/vmax         : Sets the maximum verbose level.")
    print()
    print("/yes          : Suppress inputs by answering \"yes\" (or the equivalent).")
    print("/echo         : Echoes the command to be run, including arguments, before running it.")
    print("                Append -success or -fail to echo the command when the target returns a success or failure error code.")
    print("/dry          : Does not actually run the target executable.")
    print("/list         : Alias for /echo + /dry.")
    print("/target       : Print only the target and exit. Implies /qmax and /dry.")
    print("/autopipe     : If stdin is a pipe, automatically prepend a papply argument. Otherwise, does nothing.")
    print("/autosilent   : If stdout is a pipe, silence all output")
    print()
    print("/cd           : Runs the target in the target's directory, instead of the current one.")
    print("                Append a -[path] to execute in the specified directory")
    print("/elevate      : Requests elevation before running the target. Might break stdin/out/err pipes.")
    print("/fork         : Does not wait for the started process to end.")
    print("/detach       : Detaches child processes, but can create unwanted windows. Usually used with /fork.")
    print("/waitfor-XX   : Delays execution until after the specified process (PID) has stopped running. Can be repeated.")
    print("                Requires the \"psutil\" python module.")
    print("/waitforqueue : Waits for all other (if any) go instances that use this option.")
    print("                Requires the \"ilock\" and \"psutil\" pip modules.")
    print("/priority[+=-]XX : Change the target process' priority. + and - change the value relative to the current")
    print("                       process' priority, while = sets it directly.")
    print("                   XX is an integer in the range: [-2, 3] on Windows, [-20, 20] otherwise.")
    print("                   Requires the \"psutil\" python module on Windows.")
    print("/parallel     : Starts all instances, and then waits for all. Valid only with /*apply argument.")
    print("/limit-XX     : Limits parallel runs to have at most XX targets running at once.")
    print("/batch-XX     : Batches parallel runs in sizes of XX. Valid only after /parallel.")
    print("/shell        : Run the command through the default shell interpreter. Allows for any target.")
    print("/asscript     : Passes all commands to the default shell interpreter, as a file. Incompatible with most modifiers.")
    print("                Overrides the target to be run with the default shell interpreter, and allows for any target.")
    print("                Appending a + after the argument will not disable shell echo. (/asscript+)")
    print("/unsafe       : Run the command as a simple string, and don't escape anything if possible.")
    print()
    print("/noinline     : Disable replacement of inline markers.")
    print("/repeat-XX    : Repeats the execution XX times (before any apply list trimming is done).")
    print("/rollover[+-] : Sets apply parameters to run as many times as possible.")
    print("                + (default) and - control whether to repeat source lists that are smaller, or to pass empty.")
    print("/crossjoin    : Cross-joins all apply lists, resulting in all possible argument combinations.")
    print("/[type]apply  : For every line in the specified source, runs the target with the line added as arguments.")
    print("                If no inline markers (see below) are specified, all arguments are appended to the end.")
    print("                Accepts a number of modifiers with +[modifier], after any apply-specific arguments.")
    print("                Apply-specific arguments must always come first: [apply type](-[arguments])?(\\+[modifier])*")
    print("                Types of apply:")
    print("                    C:   reads the input text from the clipboard as lines")
    print("                    D:   needs an *-int, duplicates the specified /*apply list, without any of its modifiers")
    print("                    F:   reads the lines of a file, specified with *-path")
    print("                    G:   reads the output lines of a go command, specified with *-command; max quiet level is implied")
    print("                         allows any standard go arguments (eg: \"/gapply-/iapply-1,2,3 cmd /c echo\"")
    print("                    H:   fetches lines from the specified URL")
    print("                    I:   reads the immediate string as a comma separated list, specified with *-text")
    print("                    P:   reads the input lines from stdin until EOF; returns the same arguments if used again")
    print("                    PY:  uses the specified py script to fetch an apply list; accepts *-path[,arg]; see go /modulehelp")
    print("                    R:   generates a range of numbers and accepts 1 to 3 comma-separated parameters (python range(...))")
    print("                    U:   needs an *-int, works similar to D, but includes its modifiers")
    print("                Modifiers:")
    print("                    d        don't insert the argument if it's not explicitly referenced")
    print("                    e        shell-escapes the argument")
    print("                    f[fi]:fmt  format the string using a standard printf format")
    print("                             append an \"i\" or \"f\" (eg. fi/ff) to treat the input as ints or floats")
    print("                    fl:sep   flatten the argument list to a single arg and join the elements with the given separator")
    print("                    g:args   run go with the specified arguments to process the incoming list and return a new one")
    print("                             the sub-go will receive its arguments with via stdin, so /papply should be used")
    print("                    i:x      inserts the argument in the command at the specified 0-based index")
    print("                    py:path[,arg]  uses the specified py script to modify an apply list; see go /modulehelp")
    print("                    rep:x:y  replaces the string x in the input with the string y")
    print("                    rm:rgx   filters out arguments that don't match (anywhere) the specified regex")
    print("                    rs:rgx   returns group 1 (else the first match) using the specified regex, for every argument")
    print("                             appending a number after rs will select that group instead of the first one (eg. rs3:...)")
    print("                    rms:rgx  equivalent to rm:rgx followed by a rs:rgx; allows setting a group number like \"rs:rgx\"")
    print("                    s:expr   extract only the specified argument indexes from the source list; use s-:expr to invert")
    print("                             expr is a comma-separated list of python-like array indexer")
    print("                             indices are processed in the given order")
    print("                    sp:pat   split all agruments into more arguments, separated by the given pat regex pattern")
    print("                             excludes blank parts")
    print("                    ss:x:y:z  extracts a substring from the argument with a python-like array indexer expression")
    print("                    [lr]strip[:x]  strips whitespace characters from the ends of the argument")
    print("                             prepend \"l\" or \"r\" to strip to trim only that side of the argument")
    print("                             append a :string to strip to trim only those specific characters")
    print("                    tsp      transpose an argument list to multiple chained arguments; this modifier must come last")
    print("                    w:pat    retains only arguments that match the specified wildcard pattern; use w-:pat to invert")
    print("                    xtr:pat  extracts the specified regex match from all arguments, and then flattens the result")
    print("                             returns group 1 (else the first match), or allows a group number like rs:rgx")
    print("                Inline (inside command arguments) markers:")
    print("                    Syntax: %%[<nothing> | apply argument | index of apply source]%%.")
    print("                    You can use $ instead of % if your shell treats either one differently.")
    print("                    Inline markers specify where to append the apply lists, including in quoted or complex arguments.")
    print("                    Apply lists can be used more than one time.")
    print("                    Specifying no argument, the next apply list will be used.")
    print("                    Specifying a numeric index, including negatives, will use that specific apply list.")
    print("                    Specifying an apply argument (eg. %%fapply-files.txt%% will create a new apply list and use it.")
    print("                        The i modifier cannot be used in this case")
    print("                    Specifying a numeric index and any modifiers will create a \"dapply\" marker with the same arguments.")
    print("                    \"Escaping\" or indenting an inline marker (eg. when running nested go's) is done with prepending")
    print("                        a number of '#' before the marker, similar to indented code.")


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
    print("    go /rapply-1,100+[fi:%03d] cmd /c echo")
    print()
    print("Print last 4 characters of all files in the current directory, read from stdin:")
    print("    dir /b | go /papply+[ss:-4:] cmd /c echo")
    print()
    print("Print only the extensions of all files in the current directory, read from stdin; not using [^.]+ due to parsing issues:")
    print("    dir /b | go /papply+[rs:\\..+?$] cmd /c echo")
    print()
    print("Concatenate files using cmd's copy and go's format+flatten:")
    print("    dir /b *.bin | go /asscript /papply+[f:\\\"%s\\\"]+[fl:+] copy /b %%%% out.bin")


def PrintModulehelp():
    if not can_print(2):
        return

    print("Go can be extended with external python modules (scripts), allowing for dynamic creation or modification of apply arguments.")
    print("A go module can contain any code, and can implement any number of the 4 top-level functions, seen below:")
    print("    Init(config):  initializes the module, with the specified GoConfig; called only once at startup")
    print("    Exit():  clean up the module, if necessary; called only once at end of go")
    print("    GetApplyList(context, argument):  return a list of strings to be used as an apply source (context); accepts a string argument")
    print("    ModifyApplyList(context, applyList, argument):  modify the source (context) list of strings (applyList) and return a list of strings; accepts a string argument")
    print("Go modules can be placed in the \"go_modules\" directory created next to go.py, and they will be seen automatically.")


class Updater():
    SCRIPT_URL_PREFIX = "https://raw.githubusercontent.com/Spavid04/go/master/"

    @staticmethod
    def TryUpdate():
        prnt = Cprint_gen(2)

        currentVersion = get_current_version()
        prnt(">>>current version:\t[revision %s    version date %s]" % currentVersion)

        beginningText = Utils.GetTextFromUrl(Updater.SCRIPT_URL_PREFIX + "go.py", (0, 50))
        newVersion = parse_version(beginningText.splitlines()[0])
        if currentVersion >= newVersion:
            prnt(">>>server has:\t\t[revision %s    version date %s]" % newVersion)
            if currentVersion == newVersion:
                prnt(">>>you are using the newest version!")
            else:
                prnt(">>>you are using a newer version!")
            exit(0)

        prnt(">>>new version available! [revision %s    version date %s]" % newVersion)
        prnt(">>>source: %s" % (Updater.SCRIPT_URL_PREFIX + "go.py"))

        prnt(">>>update? (Y/n): ")
        choice = input()

        if len(choice) > 0 and choice[0].lower() == "n":
            prnt(">>>update cancelled")
            exit(0)

        newScriptText = Utils.GetTextFromUrl(Updater.SCRIPT_URL_PREFIX + "go.py")
        with open(__file__, "w", encoding="utf-8") as f:
            f.write(newScriptText)

        prnt(">>>all ok!")
        exit(0)


class MatchCacheItem():
    def __init__(self, path: str, filename: str):
        self.path = path
        self.filename = filename
        self.linkTarget : typing.Optional[str] = None

class MatchCache():
    def __init__(self, timestamp: float, paths: typing.List[MatchCacheItem]):
        self.version = get_current_version()
        self.timestamp = timestamp
        self.paths = paths

    def GoodVersion(self) -> bool:
        return self.version == get_current_version()

class ApplyListSpecifier():
    __ApplyRegex = re.compile(r"^(?:([cdfghipru]|py)apply|(-?\d+))(.+)?$", re.I)
    __ApplyArgumentRegex = re.compile(r"(?: \+\[(.+?)\] | -(.+?) ) (?=$|\+\[)", re.I | re.X)

    def __init__(self,
                 sourceText: str,
                 sourceType: str,
                 modifiers: typing.Optional[typing.List[typing.Tuple[str, typing.Any]]] = None,
                 source: typing.Optional[str] = None):
        self.SourceText = sourceText
        self.SourceType = sourceType
        self.Modifiers = modifiers if modifiers is not None else []
        self.Source = source

        self.List = None
        self.Used = False

    @property
    def ShouldTranspose(self) -> bool:
        return any(x == "tsp" for (x, _) in self.Modifiers)

    @staticmethod
    def TryParse(text: str) -> typing.Optional["ApplyListSpecifier"]:
        m = ApplyListSpecifier.__ApplyRegex.match(text)
        if not m:
            return None

        groups = m.groups()
        if groups[1] is None:
            type = groups[0]
            argsstr = groups[2]
        else:
            # %%number+modifiers%% becomes %%dapply-number+modifiers
            type = "d"
            argsstr = "-" + groups[1] + groups[2]
        modifiers = []
        applyArgument = None

        if argsstr is not None:
            for match in ApplyListSpecifier.__ApplyArgumentRegex.finditer(argsstr):
                if match.group(1):
                    modifierText = match.group(1)
                    if modifierText == "d":
                        modifiers.append(("d", None))
                    elif modifierText == "e":
                        modifiers.append(("e", None))
                    elif m := re.match("(f[fi]?):(.+)", modifierText, re.I):
                        modifiers.append((m.group(1), m.group(2)))
                    elif m := re.match("fl:(.+)?", modifierText, re.I):
                        separator = m.group(1) or ""
                        modifiers.append(("fl", separator))
                    elif m := re.match("g:(.+)", modifierText, re.I):
                        modifiers.append(("g", m.group(1)))
                    elif m := re.match("i:(\\d+)", modifierText, re.I):
                        modifiers.append(("i", int(m.group(1))))
                    elif m := re.match("py:([^,]+)(?:,(.+))?", modifierText, re.I):
                        modulePath = m.group(1)
                        moduleArgument = m.group(2)
                        modifiers.append(("py", (modulePath, moduleArgument)))
                    elif m := re.match("rep:([^:]+):?(.+)?", modifierText, re.I):
                        x = m.group(1)
                        y = m.group(2) or ""
                        modifiers.append(("rep", (x, y)))
                    elif m := re.match("(r[ms]+)(\\d+)?:(.+)", modifierText, re.I):
                        modifierType = m.group(1)
                        groupNumber = 1
                        modifierValue = m.group(3)
                        if m.group(2):
                            groupNumber = int(m.group(2))

                        if modifierType == "rm":
                            modifiers.append((modifierType, modifierValue))
                        elif modifierType == "rs":
                            modifiers.append((modifierType, (groupNumber, modifierValue)))
                        elif modifierType == "rms":
                            modifiers.append(("rm", modifierValue))
                            modifiers.append(("rs", (groupNumber, modifierValue)))
                    elif m := re.match("s(-?):([\\d:,-]+)", modifierText, re.I):
                        excludeInstead = bool(m.group(1))
                        expression = m.group(2)
                        modifiers.append(("s", (excludeInstead, expression)))
                    elif m := re.match("sp:(.+)", modifierText, re.I):
                        modifiers.append(("sp", m.group(1)))
                    elif m := re.match("ss:([\\d:,-]+)", modifierText, re.I):
                        modifiers.append(("ss", m.group(1)))
                    elif m := re.match("([lr])?strip(?::(.+))?", modifierText, re.I):
                        side = m.group(1)
                        characters = m.group(2)
                        modifiers.append(("strip", (side, characters)))
                    elif "tsp" == modifierText.lower():
                        modifiers.append(("tsp", None))
                    elif m := re.match("w(-)?:(.+)", modifierText, re.I):
                        inverted = bool(m.group(1))
                        pattern = m.group(2)
                        modifiers.append(("w", (inverted, pattern)))
                    elif m := re.match("xtr(\\d+)?:(.+)", modifierText, re.I):
                        groupNumber = 1
                        pattern = m.group(2)
                        if m.group(1):
                            groupNumber = int(m.group(1))

                        modifiers.append(("xtr", (groupNumber, pattern)))

                elif match.group(2):
                    applyArgument = match.group(2)

        return ApplyListSpecifier(text, type, modifiers, applyArgument)


class InlineMarkerSpecifier():
    __InlineMarkerRegex = re.compile(r"(\#*)(%%|\$\$)(-?\d+|.+?)??(%%|\$\$)", re.I)

    def __init__(self, index: typing.Optional[int]):
        self.Index = index

        self.ApplyList : typing.Optional[ApplyListSpecifier] = None

    @property
    def ShouldTranspose(self) -> bool:
        return self.ApplyList.ShouldTranspose

    @staticmethod
    def TryParseMarkers(text: str) \
            -> typing.Optional[typing.List[typing.Union[str, "InlineMarkerSpecifier", ApplyListSpecifier]]]:
        split = InlineMarkerSpecifier.__InlineMarkerRegex.split(text)
        if len(split) <= 1:
            return None

        toReturn = [split[0]]
        i = 1
        n = len(split)
        while i < n:
            indentStr = split[i]
            (mkStart, content, mkEnd) = split[i + 1:i + 4]
            suffix = split[i + 4]
            i += 5

            if indentStr:
                piece = indentStr[1:] + mkStart + (content or "") + mkEnd
            elif not content:
                piece = InlineMarkerSpecifier(None)
            elif (intValue := Utils.TryParseInt(content)) is not None:
                piece = InlineMarkerSpecifier(intValue)
            elif (specifier := ApplyListSpecifier.TryParse(content)) is not None:
                piece = specifier
            else:
                piece = content

            toReturn.append(piece)
            toReturn.append(suffix)

        return toReturn


class ExternalModule():
    def __init__(self, path: str):
        self.path = path

        moduleName = os.path.splitext(os.path.split(self.path)[1])[0]
        self.spec = importlib.util.spec_from_file_location(moduleName, self.path)
        self.module = importlib.util.module_from_spec(self.spec)
        self.spec.loader.exec_module(self.module)

        self._has_GetApplyList = hasattr(self.module, "GetApplyList")
        self._has_ModifyApplyList = hasattr(self.module, "ModifyApplyList")

    def Init(self, config: "GoConfig"):
        if hasattr(self.module, "Init"):
            self.module.Init(config)

    def Exit(self):
        if hasattr(self.module, "Exit"):
            self.module.Exit()

    def GetApplyList(self, context: ApplyListSpecifier, argument: typing.Optional[str]) -> typing.List[str]:
        if self._has_GetApplyList:
            return self.module.GetApplyList(context, argument)
        else:
            raise NotImplementedError()

    def ModifyApplyList(self, context: ApplyListSpecifier, applyList: typing.List[str], argument: typing.Optional[str]) -> typing.List[str]:
        if self._has_ModifyApplyList:
            return self.module.ModifyApplyList(context, applyList, argument)
        else:
            raise NotImplementedError()


class GoFilter():
    def __init__(self, path: str):
        self.Path = path

        self.Includes: typing.List[str] = []
        self.Excludes: typing.List[str] = []
        self.SubIncludes: typing.List[str] = []
        self.SubExcludes: typing.List[str] = [] # todo

        self.__Read()

    def __Read(self):
        with open(self.Path, "r") as f:
            gofilterFilters = f.read().splitlines()

        for line in gofilterFilters:
            hasSubdir = "/" in line or "\\" in line

            if line.startswith("+"):
                if hasSubdir:
                    self.SubIncludes.append(line[1:])
                else:
                    self.Includes.append(line[1:])
            else:
                text = line
                if text.startswith("-"):
                    text = text[1:]
                if hasSubdir:
                    self.SubExcludes.append(text)
                else:
                    self.Excludes.append(text)

    def Match(self, text: str) -> typing.Literal[-1, 1]:
        if any(fnmatch.fnmatch(text, x) for x in self.Includes):
            return 1
        if any(fnmatch.fnmatch(text, x) for x in self.Excludes):
            return -1
        return 1


class Utils():
    __isWindows = None
    @staticmethod
    def IsWindows() -> bool:
        if Utils.__isWindows is None:
            Utils.__isWindows = (sys.platform == "win32")
        return Utils.__isWindows

    __COLORAMA_INITED = False
    @staticmethod
    def TryInitColorama() -> bool:
        if not COLORAMA_AVAILABLE:
            return False
        if Utils.__COLORAMA_INITED:
            return True

        try:
            colorama.init()
            Utils.__COLORAMA_INITED = True
            return True
        except ModuleNotFoundError:
            Cprint(">>>colorama module not found; clearing screen the classic way", level=1)
            return False

    @staticmethod
    def ClearScreen():
        if COLORAMA_AVAILABLE and Utils.__COLORAMA_INITED:
            print(colorama.ansi.clear_screen())
        else:
            if Utils.IsWindows():
                os.system("cls")
            else:
                os.system("clear")

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
    def IsHidden(path: str) -> bool:
        if Utils.IsWindows():
            s = os.stat(path)
            return bool(s.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
        else:
            filename = os.path.split(path)[1]
            return filename[0] == "."

    @staticmethod
    def ParsePathsForFiles(targetedPaths: typing.List[str], extensions: typing.List[str],
                           recursive: bool, includeModX: bool, includeHidden: bool,
                           ignoredPaths: typing.Optional[typing.List[str]] = None) -> \
            typing.List[typing.Tuple[str, str]]:
        matches = []
        matchingPaths = set()

        ignoredFiles = [os.path.normcase(os.path.normpath(x)) for x in ignoredPaths if os.path.isfile(x)] if ignoredPaths else []
        ignoredDirectories = [os.path.normcase(os.path.normpath(x)) for x in ignoredPaths if os.path.isdir(x)] if ignoredPaths else []

        pathQueue = queue.SimpleQueue()
        for i in targetedPaths:
            pathQueue.put(i)

        while not pathQueue.empty():
            targetedPath = pathQueue.get()

            if os.path.isfile(targetedPath):
                abspath = os.path.normcase(os.path.normpath(os.path.abspath(targetedPath)))
                file = os.path.split(abspath)[1]
                if abspath in matchingPaths:
                    continue
                matches.append((abspath, file))
                matchingPaths.add(abspath)
            else:
                for (root, dirs, files) in os.walk(targetedPath, topdown=True):
                    if not config.IgnoreGofilters:
                        if ".gofilter" in files:
                            gofilterName = ".gofilter"
                        elif "go.filter" in files:
                            gofilterName = "go.filter"
                        else:
                            gofilterName = None
                        
                        if gofilterName:
                            files.remove(gofilterName)
                            gofilter = GoFilter(os.path.join(root, gofilterName))

                            for dir in list(dirs):
                                if gofilter.Match(dir) == -1:
                                    dirs.remove(dir)

                            for file in list(files):
                                if gofilter.Match(file) == -1:
                                    files.remove(file)

                            for item in gofilter.SubIncludes:
                                abspath = os.path.abspath(os.path.join(root, os.path.normcase(item)))
                                pathQueue.put(abspath)

                    if recursive and (ignoredDirectories or not includeHidden):
                        dirs_copy = list(dirs)
                        for dir in dirs_copy:
                            abspath = os.path.abspath(os.path.join(root, dir))
                            if not includeHidden and Utils.IsHidden(abspath):
                                dirs.remove(dir)
                                continue

                            ignored = False
                            normalized = os.path.normcase(os.path.normpath(abspath))
                            for ignoredDirectory in ignoredDirectories:
                                if os.path.samefile(normalized, ignoredDirectory) \
                                        or normalized.startswith(ignoredDirectory):
                                    ignored = True
                                    break
                            if ignored:
                                dirs.remove(dir)
                                continue

                    for file in files:
                        fullpath = os.path.join(root, file)
                        if "/" in file or "\\" in file:
                            file = os.path.split(file)[1]

                        if not includeHidden:
                            if Utils.IsHidden(fullpath):
                                continue
                        if ignoredFiles:
                            if any(os.path.samefile(fullpath, x) for x in ignoredFiles):
                                continue

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

    __Compare_RegexObject = None
    __Compare_SequenceMatcher = difflib.SequenceMatcher()
    @staticmethod
    def ComparePathAndPattern(file: str, pattern: str, fuzzy: bool, asRegex: bool, asWildcard: bool) \
            -> float:
        if Utils.IsWindows():
            file = file.lower()
        (filename, _) = os.path.splitext(file)

        if not fuzzy:
            if Utils.IsWindows():
                pattern = pattern.lower()

            return int(filename == pattern or file == pattern)
        elif asRegex:
            if Utils.__Compare_RegexObject is None:
                Utils.__Compare_RegexObject = re.compile(pattern, re.I)

            if Utils.__Compare_RegexObject.match(filename) or Utils.__Compare_RegexObject.match(file):
                return 1
            else:
                return 0
        elif asWildcard:
            if Utils.IsWindows():
                pattern = pattern.lower()

            return int(fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(file, pattern))
        else:
            if Utils.IsWindows():
                pattern = pattern.lower()

            sm = Utils.__Compare_SequenceMatcher
            sm.set_seq2(pattern)
            sm.set_seq1(filename); r1 = sm.ratio()
            sm.set_seq1(file); r2 = sm.ratio()
            return max(r1, r2)

    @staticmethod
    def PathContains(path: str, substring: str) -> bool:
        (directory, _) = os.path.splitext(path)

        return substring.lower() in directory.lower()

    __Clipboard_ValuesInitialized = False
    __Clipboard_Kernel32 = None
    __Clipboard_User32 = None
    @staticmethod
    def __classicGetClipboardWindows() -> str:
        if not Utils.__Clipboard_ValuesInitialized:
            Utils.__Clipboard_Kernel32 = ctypes.windll.kernel32
            Utils.__Clipboard_Kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            Utils.__Clipboard_Kernel32.GlobalLock.restype = ctypes.c_void_p
            Utils.__Clipboard_Kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            Utils.__Clipboard_User32 = ctypes.windll.user32
            Utils.__Clipboard_User32.GetClipboardData.restype = ctypes.c_void_p

            Utils.__Clipboard_ValuesInitialized = True

        Utils.__Clipboard_User32.OpenClipboard(0)
        try:
            if Utils.__Clipboard_User32.IsClipboardFormatAvailable(1):  # CF_TEXT
                data = Utils.__Clipboard_User32.GetClipboardData(1)  # CF_TEXT
                data_locked = Utils.__Clipboard_Kernel32.GlobalLock(data)
                text = ctypes.c_char_p(data_locked)
                value = text.value
                Utils.__Clipboard_Kernel32.GlobalUnlock(data_locked)
                return value.decode("utf-8")
        finally:
            Utils.__Clipboard_User32.CloseClipboard()

        return ""

    @staticmethod
    def _termuxTryGetClipboard() -> typing.Optional[str]:
        if Utils.IsWindows():
            return None
        if not shutil.which("termux-setup-storage"):
            return None
        if not shutil.which("termux-clipboard-get"):
            Cprint(">>>termux requires Termux:API to be installed for the clipboard to work", level=2)
            return None
        tcg = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, encoding="utf-8")
        if tcg.returncode != 0:
            return ""
        return tcg.stdout

    @staticmethod
    def GetClipboardText() -> str:
        if (c := Utils._termuxTryGetClipboard()) is not None:
            return c
        elif PYPERCLIP_AVAILABLE:
            return pyperclip.paste()
        elif Utils.IsWindows():
            Cprint(">>>pyperclip module not found; defaulting to classic ctypes method", level=1)
            return Utils.__classicGetClipboardWindows()
        else:
            Cprint(">>>pyperclip module not found; clipboard will not work!", level=2)
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
    def CaptureGoOutput(command: str, stdinLines: typing.List[str] = None) -> typing.List[str]:
        lines = []

        process = subprocess.Popen("go /qmax " + command, shell=True,
                                   stdout=subprocess.PIPE, stderr=sys.stderr, stdin=subprocess.PIPE if stdinLines else sys.stdin)

        if stdinLines:
            (stdout, _) = process.communicate(input=os.linesep.join(stdinLines).encode("utf-8"))
            stdout = stdout.splitlines()
        else:
            stdout = process.stdout

        for line in stdout:
            lines.append(line.rstrip().decode("utf-8"))

        return lines

    @staticmethod
    def StreamOutput(process: subprocess.Popen) -> typing.Generator[bytes, None, None]:
        stdout = process.stdout
        stderr = process.stderr

        newLineSemaphore = threading.Semaphore(0)

        stdoutData = queue.Queue()
        stderrData = queue.Queue()

        def helperThread(stream: typing.IO, eventSemaphore: threading.Semaphore, outList: queue.Queue[bytes]):
            for line in stream:
                outList.put(line)
                eventSemaphore.release()
            eventSemaphore.release()

        stdoutThread = threading.Thread(target=helperThread, args=(stdout, newLineSemaphore, stdoutData), daemon=True)
        stderrThread = threading.Thread(target=helperThread, args=(stderr, newLineSemaphore, stderrData), daemon=True)

        stdoutThread.start()
        stderrThread.start()

        while True:
            newLineSemaphore.acquire()

            source = None

            if not stdoutData.empty():
                source = stdoutData
            elif not stderrData.empty():
                source = stderrData
            else:
                newLineSemaphore.acquire()
                if not stdoutThread.is_alive() and not stderrThread.is_alive():
                    break

            yield source.get()

    @staticmethod
    def RemoveControlCharacters(s):
        return "".join(ch if unicodedata.category(ch)[0] != "C" else " " for ch in s)

    @staticmethod
    def EnsureAdmin():
        hasAdmin = False

        if Utils.IsWindows():
            try:
                hasAdmin = ctypes.windll.shell32.IsUserAnAdmin()
            except:
                pass
        else:
            hasAdmin = (os.geteuid() == 0)

        if hasAdmin:
            return

        executable = Utils.EscapeForShell(sys.executable)
        args = [Utils.EscapeForShell(x) for x in sys.argv]

        if Utils.IsWindows():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, Utils.JoinForShell(args, False), None, 1)
        else:
            subprocess.Popen(["sudo", executable, *args])
        exit(0)

    @staticmethod
    def Batch(list: typing.List[object], batchSize: int) -> typing.Generator[typing.List[object], None, None]:
        length = len(list)
        for i in range(0, length, batchSize):
            yield list[i:min(i + batchSize, length)]

    @staticmethod
    def CreateScriptFile(items: typing.List[typing.List[str]], echoOff: bool, unsafe: bool = False) -> str:
        if Utils.IsWindows():
            echo = "@echo off"
            suffix = ".bat"
            selfDelete = "(goto) 2>nul & del \"%~f0\""
        else:
            # does this even work?
            echo = "set echo off"
            suffix = ".sh"
            selfDelete = "rm -- \"$0\""

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=suffix, delete=False, newline=None) as f:
            if echoOff:
                f.write(echo)
                f.write("\n")

            for r in items:
                f.write(Utils.JoinForShell(r, not unsafe))
                f.write("\n")

            f.write(selfDelete)
            f.write("\n")

            script = f.name

        os.chmod(script, 0o755)
        return script

    __Escape_Windows_Chars = "()%!^\"<>&|"
    __Escape_Windows_Re = re.compile("(" + "|".join(re.escape(char) for char in list(__Escape_Windows_Chars)) + ")")
    __Escape_Windows_Map = {char: "^%s" % char for char in __Escape_Windows_Chars}
    @staticmethod
    def EscapeForShell(text: str) -> str:
        if Utils.IsWindows():
            if not text or re.search(r"([\"\s])", text):
                text = "\"" + text.replace("\"", r"\"") + "\""

            def escape_meta_chars(m):
                char = m.group(1)
                return Utils.__Escape_Windows_Map[char]

            return Utils.__Escape_Windows_Re.sub(escape_meta_chars, text)
        else:
            return shlex.quote(text)

    @staticmethod
    def JoinForShell(args: typing.Iterable[str], escape: bool = True) -> str:
        if escape:
            processed = (Utils.EscapeForShell(x) for x in args)
        else:
            processed = args

        if Utils.IsWindows():
            return " ".join(processed)
        else:
            return shlex.join(processed)

    class ProcessWaiter():
        __PIDS_FILE = os.path.join(tempfile.gettempdir(), "go.waitqueue")
        __ILOCK_NAME = "go-waitqueue"

        def __init__(self):
            self.test = 0
            self._pids: typing.List[int] = []
            self._useQueueing = False

        @staticmethod
        def FromPids(pids: typing.List[int]) -> "Utils.ProcessWaiter":
            if not PSUTIL_AVAILABLE:
                Cprint(">>>psutil module not found!", level=2)
                raise ModuleNotFoundError("psutil")

            pw = Utils.ProcessWaiter()
            pw._pids = list(pids)
            return pw

        @staticmethod
        def _GetFilePids() -> typing.List[int]:
            try:
                with open(Utils.ProcessWaiter.__PIDS_FILE, "r", newline="") as f:
                    return [int(x) for x in f.read().splitlines()]
            except:
                return []

        @staticmethod
        def _SetFilePids(pids: typing.List[int]):
            try:
                with open(Utils.ProcessWaiter.__PIDS_FILE, "w", newline="") as f:
                    f.write(os.linesep.join(str(x) for x in pids))
            except:
                pass

        @staticmethod
        def FromQueue() -> "Utils.ProcessWaiter":
            if not ILOCK_AVAILABLE or not PSUTIL_AVAILABLE:
                Cprint(">>>ilock or psutil modules not found!", level=2)
                raise ModuleNotFoundError("ilock or psutil")

            pw = Utils.ProcessWaiter()
            pw._useQueueing = True
            return pw

        @staticmethod
        def WaitForPids(pids: typing.List[int]):
            if not pids:
                return
            if not PSUTIL_AVAILABLE:
                Cprint(">>>psutil module not found!", level=2)
                raise ModuleNotFoundError("psutil")

            Cprint("Waiting for: " + ", ".join(str(x) for x in pids))

            exited = [False] * len(pids)
            while not all(exited):
                for i in range(len(pids)):
                    if exited[i]:
                        continue

                    exists = psutil.pid_exists(pids[i])
                    if not exists:
                        exited[i] = True
                        Cprint(str(pids[i]) + " exited")
                time.sleep(0.1)

        def __add__(self, other: "Utils.ProcessWaiter") -> "Utils.ProcessWaiter":
            if other is None:
                return self
            if not isinstance(other, Utils.ProcessWaiter):
                raise Exception("Cannot add ProcessWriter with something else!")

            pw = Utils.ProcessWaiter()
            pw._pids = self._pids + other._pids
            pw._useQueueing = self._useQueueing or other._useQueueing
            return pw

        def __enter__(self):
            pids = []

            if self._useQueueing:
                with ilock.ILock(Utils.ProcessWaiter.__ILOCK_NAME):
                    pids = [x for x in Utils.ProcessWaiter._GetFilePids() if psutil.pid_exists(x)]
                    self._pids = [*pids, os.getpid()]
                    Utils.ProcessWaiter._SetFilePids(self._pids)
            else:
                pids = self._pids

            Utils.ProcessWaiter.WaitForPids(pids)
            return self

        def __exit__(self, _, __, ___):
            if self._useQueueing:
                with ilock.ILock(Utils.ProcessWaiter.__ILOCK_NAME):
                    currentPid = os.getpid()
                    pids = [x for x in Utils.ProcessWaiter._GetFilePids()
                            if (x != currentPid) and psutil.pid_exists(x)]
                    Utils.ProcessWaiter._SetFilePids(pids)

    @staticmethod
    def GetTextFromUrl(url: str, range: typing.Tuple[int, int] = None) -> str:
        request = urllib.request.Request(url)
        if range is not None:
            request.headers["Range"] = "bytes=%d-%d" % range
        with urllib.request.urlopen(request) as f:
            return f.read().decode("utf-8")

    @staticmethod
    def GetDefaultExecutableExtensions() -> typing.List[str]:
        if Utils.IsWindows():
            extensions = {".exe", ".com", ".bat", ".cmd", ".ps1", ".py"}
            extensions.update(x.lower() for x in os.environ["PATHEXT"].split(os.pathsep))
            extensions = list(extensions)
        else:
            extensions = [".sh", ".py"]
        return extensions

    @staticmethod
    def GetSliceFunc(sliceText: str) -> typing.Optional[typing.Callable]:
        m = re.match("^(-?\\d+)?(:)?(-?\\d+)?(:)?(-?\\d+)?$", sliceText, re.I)
        if not m:
            return None

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
        return func

    @staticmethod
    def ApplySlices(slices: typing.List[typing.Callable], sourceArray: list, excludeSlicesInsteadOfInclude: bool) -> typing.Optional[list]:
        if len(sourceArray) == 0:
            return []
        if len(slices) == 0 and excludeSlicesInsteadOfInclude:
            return sourceArray

        # the following is utter shit, but it works
        indices = list(range(len(sourceArray)))
        chosenIndices = []
        for s in slices:
            sliceIndices = s(indices)
            if isinstance(sliceIndices, int):
                chosenIndices.append([sliceIndices])
            else:
                chosenIndices.append(sliceIndices)

        if excludeSlicesInsteadOfInclude:
            for s in chosenIndices:
                for i in s:
                    indices[i] = -1
            return [sourceArray[x] for x in indices if x != -1]
        else:
            recreatedArray = []
            for s in chosenIndices:
                for i in s:
                    recreatedArray.append(sourceArray[i])
            return recreatedArray

    @staticmethod
    def TryParseInt(text: str) -> typing.Optional[int]:
        try:
            return int(text)
        except ValueError:
            return None

    @staticmethod
    def InsertMany(into: list, at: int, what: typing.Iterable):
        for item in what:
            into.insert(at, item)
            at += 1

    @staticmethod
    def CompactStrings(items: typing.List[typing.Union[str, typing.Any]]) -> typing.List[typing.Union[str, typing.Any]]:
        result = list()
        accumulator = list()

        for item in items:
            if isinstance(item, str):
                accumulator.append(item)
            else:
                if len(accumulator) > 0:
                    result.append("".join(accumulator))
                    accumulator.clear()
                result.append(item)
        if len(accumulator) > 0:
            result.append("".join(accumulator))

        return result

    class RepeatGenerator():
        def __init__(self, item, count: int):
            self.item = item
            self.count = count
            self.i = 0

        def __len__(self):
            return self.count

        def __iter__(self):
            self.i = 0
            return self

        def __next__(self):
            if self.i < self.count:
                self.i += 1
                return self.item
            else:
                raise StopIteration

    class PriorityModifier():
        __Inited = None
        __WindowsPriorityClasses = None

        def __init__(self, priorityOrOffset: int, offset: bool):
            assert(Utils.PriorityModifier.__setup())

            self.PriorityOrOffset = priorityOrOffset
            self.Offset = offset

            self.__originalPriority: typing.Optional[int] = None
            self.__skip = (priorityOrOffset == 0 and offset == True)

        def __enter__(self):
            if self.__skip:
                return self

            selfPid = os.getpid()

            self.__originalPriority = Utils.PriorityModifier.GetPriority(selfPid)
            Utils.PriorityModifier.SetPriority(selfPid, self.PriorityOrOffset, self.Offset)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.__skip:
                return
            Utils.PriorityModifier.SetPriority(os.getpid(), self.__originalPriority, False)

        @staticmethod
        def __setup() -> bool:
            if Utils.PriorityModifier.__Inited is not None:
                return Utils.PriorityModifier.__Inited

            if Utils.IsWindows():
                if not PSUTIL_AVAILABLE:
                    Cprint(">>>psutil module not found; /priority will not work!", level=2)
                    Utils.PriorityModifier.__Inited = False
                    return False

                if Utils.PriorityModifier.__WindowsPriorityClasses is None:
                    mapping = {
                        -2: psutil.IDLE_PRIORITY_CLASS,
                        -1: psutil.BELOW_NORMAL_PRIORITY_CLASS,
                        0: psutil.NORMAL_PRIORITY_CLASS,
                        1: psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                        2: psutil.HIGH_PRIORITY_CLASS,
                        3: psutil.REALTIME_PRIORITY_CLASS,
                    }
                    Utils.PriorityModifier.__WindowsPriorityClasses = (
                        mapping,
                        {v: k for (k, v) in mapping.items()}
                    )

            Utils.PriorityModifier.__Inited = True
            return True

        @staticmethod
        def GetPriority(pid: int) -> int:
            assert (Utils.PriorityModifier.__setup())

            if Utils.IsWindows():
                priority = Utils.PriorityModifier.__WindowsPriorityClasses[1][psutil.Process(pid).nice()]
            else:
                priority = os.getpriority(os.PRIO_PROCESS, pid)

            return priority


        @staticmethod
        def SetPriority(pid: int, priorityOrOffset: int, offset: bool):
            assert(Utils.PriorityModifier.__setup())

            if offset:
                if Utils.IsWindows():
                    priority = Utils.PriorityModifier.__WindowsPriorityClasses[1][psutil.Process().nice()]
                else:
                    priority = os.getpriority(os.PRIO_PROCESS, 0)
                priorityOffset = priorityOrOffset
            else:
                priority = priorityOrOffset
                priorityOffset = 0

            newPriority = priority + priorityOffset

            if Utils.IsWindows():
                newPriority = max(-2, min(newPriority, 3))
                newPriority = Utils.PriorityModifier.__WindowsPriorityClasses[0][newPriority]
            else:
                newPriority = max(-20, min(newPriority, 20))

            psutil.Process(pid).nice(newPriority)

class EchoWhenValues(enum.Enum):
    Always = 0
    Failure = 1
    Success = 2

class GoConfig:
    _QuietRegex = re.compile("^(q+)uiet$", re.I)
    _VerboseRegex = re.compile("^(v+)erbose$", re.I)

    def __init__(self):
        self.ConfigFile = "go.config"

        self.TargetedExtensions = Utils.GetDefaultExecutableExtensions()
        self.TargetedPaths = []
        self.IgnoredPaths = []
        self.IncludeAnyExecutables = (not Utils.IsWindows())
        self.IncludeHidden = False

        self.CacheInvalidationTime = 1
        self.UsePathCache = False
        self.DisablePathCache = False
        self.RefreshPathCache = False
        self.FuzzyMatch = True
        self.IgnoreDuplicateLinks = True
        self.IgnoreGofilters = False

        self.RegexTargetMatch = False
        self.WildcardTargetMatch = False
        self.DirectoryFilter: typing.List[typing.Tuple[bool, str]] = []
        self.NthMatch = None
        self.FirstMatchFromConfig = False

        self.PrintLevel = PRINT_LEVEL

        self.EchoTarget = False
        self.EchoWhen = EchoWhenValues.Always
        self.DryRun = False
        self.AlwaysYes = False
        self.PrintTarget = False

        self.ChangeWorkingDirectory = False
        self.WorkingDirectory = None
        self.WaitForExit = True
        self.Detach = False
        self.WaitFor: typing.List[int] = []
        self.WaitForQueue = False
        self.Priority: typing.Tuple[int, bool] = (0, True)
        self.Parallel = False
        self.Batched = False
        self.ParallelLimit = None
        self.Shell = False
        self.AsShellScript = False
        self.EchoOff = True
        self.Unsafe = False

        self.ApplyLists : typing.List[ApplyListSpecifier] = []
        self.Rollover = False
        self.RolloverZero = False
        self.NoInline = False
        self.RepeatCount = None
        self.CrossJoin = False

        self.ExternalModules: typing.Dict[str, ExternalModule] = {}

        self.ReloadConfig(False)

    def ReloadConfig(self, overwriteSettings: bool):
        path = self.ConfigFile

        if os.path.abspath(path).lower() != path.lower():
            scriptDir = Utils.GetScriptDir()
            path = os.path.join(scriptDir, path)

        if not os.path.isfile(path):
            Cprint(">>>config file missing", level=1)
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                config: dict = json.load(f)
        except:
            Cprint(">>>config file contains invalid json", level=2)
            return

        targetedExtensions = config.pop("TargetedExtensions", [])
        targetedPaths = config.pop("TargetedPaths", [])
        ignoredPaths = config.pop("IgnoredPaths", [])

        if overwriteSettings:
            self.TargetedExtensions = targetedExtensions
            self.TargetedPaths = targetedPaths
            self.IgnoredPaths = ignoredPaths
        else:
            self.TargetedExtensions.extend(targetedExtensions)
            self.TargetedPaths.extend(targetedPaths)
            self.IgnoredPaths.extend(ignoredPaths)

        if config.pop("AlwaysYes", False):
            self.TryParseArgument("/yes")
        if "AlwaysQuiet" in config:
            value = config.pop("AlwaysQuiet")
            quietLevel = 0
            if isinstance(value, bool):
                if value:
                    quietLevel = 1
            else:
                quietLevel = value

            if quietLevel > 0:
                self.TryParseArgument("/yes")
                self.TryParseArgument("/" + "q" * quietLevel + "uiet")
        if config.pop("AlwaysFirst", False):
            self.FirstMatchFromConfig = True
        if config.pop("AlwaysCache", False):
            self.TryParseArgument("/cache+")
        if config.pop("AlwaysShell", False):
            self.TryParseArgument("/shell")
        if config.pop("AutoPapplyPipes", False):
            self.TryParseArgument("/autopipe")
        if config.pop("AutoSilentPipe", False):
            self.TryParseArgument("/autosilent")
        if config.pop("NoFuzzyMatch", False):
            self.TryParseArgument("/nofuzzy")
        if "IncludeHidden" in config:
            value = bool(config.pop("IncludeHidden"))
            self.TryParseArgument("/hidden" + ("+" if value else "-"))
        if "CacheInvalidationTime" in config:
            self.CacheInvalidationTime = float(config.pop("CacheInvalidationTime"))
        if "DefaultArguments" in config:
            args = config.pop("DefaultArguments")
            for arg in args:
                if not self.TryParseArgument(arg):
                    Cprint(">>>default argument \"%s\" is an invalid go argument; ignoring..." % (arg), level=2)

        self.DisablePathCache = False

        if len(config.keys()) > 0:
            Cprint(">>>config file contains extra keys: " + ", ".join(config.keys()), level=1)

    def TryParseArgument(self, argument: str) -> bool:
        if argument.startswith("/"):
            argument = argument[1:]
        elif argument.startswith("--"):
            argument = argument[2:]
        else:
            return False
        lower = argument.lower()

        if lower == "help":
            PrintHelp()
            exit(0)
        elif lower == "examples":
            PrintExamples()
            exit(0)
        elif lower == "modulehelp":
            PrintModulehelp()
            exit(0)
        elif lower == "update":
            Updater.TryUpdate()
            exit(0)

        elif lower.startswith("config-"):
            path = argument[7:]
            self.ConfigFile = path
            self.ReloadConfig(True)
        elif lower.startswith("inc"):
            action = lower[3]
            path = os.path.abspath(lower[4:])

            if action == "-":
                if path in self.TargetedPaths:
                    self.TargetedPaths.remove(path)
            else:
                if path not in self.TargetedPaths:
                    self.TargetedPaths.append(path)
            self.DisablePathCache = True
        elif lower.startswith("exc"):
            action = lower[3]
            path = os.path.abspath(lower[4:])

            if action == "-":
                if path in self.IgnoredPaths:
                    self.IgnoredPaths.remove(path)
            else:
                if path not in self.IgnoredPaths:
                    self.IgnoredPaths.append(path)
            self.DisablePathCache = True
        elif lower.startswith("ext"):
            action = lower[3]
            extension = lower[4:]

            if action == "-":
                if extension in self.TargetedExtensions:
                    self.TargetedExtensions.remove(extension)
            else:
                if extension not in self.TargetedExtensions:
                    self.TargetedExtensions.append(extension)
            self.DisablePathCache = True
        elif lower == "executables":
            self.IncludeAnyExecutables = not self.IncludeAnyExecutables
            self.DisablePathCache = True
        elif lower.startswith("hidden"):
            action = lower[6] if len(lower) == 8 else None
            if action == "+":
                self.IncludeHidden = True
            elif action == "-":
                self.IncludeHidden = False
            else:
                self.IncludeHidden = not self.IncludeHidden
            self.DisablePathCache = True

        elif lower.startswith("cache"):
            if len(lower) >= 6:
                value = lower[5]
                if value == "+":
                    self.UsePathCache = True
                elif value == "-":
                    self.UsePathCache = False
                    self.DisablePathCache = True
            else:
                self.UsePathCache = True
        elif lower == "refresh":
            self.RefreshPathCache = True
        elif lower == "nofuzzy":
            self.FuzzyMatch = False
        elif lower == "duplinks":
            self.IgnoreDuplicateLinks = False
            self.DisablePathCache = True
        elif lower == "nofilters":
            self.IgnoreGofilters = True
            self.DisablePathCache = True

        elif lower == "regex":
            self.RegexTargetMatch = True
        elif lower == "wild":
            self.WildcardTargetMatch = True
        elif lower.startswith("in"):
            mode = True if lower[2] == "+" else False
            substring = argument[3:]

            self.DirectoryFilter.append((mode, substring))
        elif lower.startswith("nth"):
            self.NthMatch = 0

            nthAsString = lower[4:]
            if len(nthAsString) > 0:
                self.NthMatch = int(nthAsString)

        elif (m := GoConfig._QuietRegex.match(argument)) or lower == "qmax":
            if m is None:
                count = MAX_QUIET_LEVEL
            else:
                count = min(len(m.group(1)), MAX_QUIET_LEVEL)

            change_level(count)
            self.PrintLevel = PRINT_LEVEL
            self.TryParseArgument("/yes")
        elif (m := GoConfig._VerboseRegex.match(argument)) or lower == "vmax":
            if m is None:
                count = MAX_VERBOSE_LEVEL
            else:
                count = min(len(m.group(1)), MAX_VERBOSE_LEVEL)

            change_level(-count)
            self.PrintLevel = PRINT_LEVEL

        elif lower == "list":
            self.TryParseArgument("/echo")
            self.TryParseArgument("/dry")
        elif lower.startswith("echo"):
            self.EchoTarget = True
            when = lower[5:]
            if when == "fail":
                self.EchoWhen = EchoWhenValues.Failure
            elif when == "success":
                self.EchoWhen = EchoWhenValues.Success
            else:
                self.EchoWhen = EchoWhenValues.Always
        elif lower == "dry":
            self.DryRun = True
        elif lower == "yes":
            self.AlwaysYes = True
        elif lower == "target":
            self.PrintTarget = True
            self.TryParseArgument("/dry")
            self.TryParseArgument("/qmax")
        elif lower == "autopipe":
            if not sys.stdin.isatty():
                self.TryParseArgument("/papply")
        elif lower == "autosilent":
            if not sys.stdout.isatty():
                self.TryParseArgument("/qmax")
                if not sys.stdin.isatty():
                    self.TryParseArgument("/yes")

        elif lower == "elevate":
            Utils.EnsureAdmin()
        elif lower.startswith("cd"):
            self.ChangeWorkingDirectory = True
            wd = argument[3:]
            if wd:
                self.WorkingDirectory = wd
        elif lower == "fork":
            self.WaitForExit = False
        elif lower == "detach":
            self.Detach = True
        elif lower.startswith("waitfor-"):
            self.WaitFor.append(int(lower[8:]))
        elif lower == "waitforqueue":
            self.WaitForQueue = True
        elif lower.startswith("priority"):
            value = int(lower[9:])
            if lower[8] == "-":
                self.Priority = (-value, True)
            elif lower[8] == "+":
                self.Priority = (value, True)
            elif lower[8] == "=":
                self.Priority = (value, False)
        elif lower == "parallel":
            self.Parallel = True
        elif lower == "batch":
            self.Batched = True
        elif lower.startswith("limit-"):
            self.ParallelLimit = int(lower[6:])
        elif lower == "shell":
            self.Shell = True
        elif lower.startswith("asscript"):
            self.AsShellScript = True
            if "+" in lower:
                self.EchoOff = False
            self.TryParseArgument("/shell")
        elif lower == "unsafe":
            self.Unsafe = True

        elif specifier := ApplyListSpecifier.TryParse(argument):
            self.ApplyLists.append(specifier)
        elif lower.startswith("rollover"):
            self.Rollover = True
            if lower.endswith("-"):
                self.RolloverZero = True
        elif lower == "noinline":
            self.NoInline = True
        elif lower.startswith("repeat-"):
            self.RepeatCount = int(lower[7:])
        elif lower == "crossjoin":
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

        if (self.Shell or self.AsShellScript) and (self.ChangeWorkingDirectory and self.WorkingDirectory is None):
            Cprint(">>>/shell or /asscript and a /cd without arguments cannot be used together", level=2)
            return False

        if self.CrossJoin and (self.RepeatCount or self.Rollover):
            Cprint(">>>/crossjoin cannot be used either /rollover or /repeat", level=2)
            return False

        if self.RegexTargetMatch and self.WildcardTargetMatch:
            Cprint(">>>/regex and /wild cannot be used together", level=2)
            return False

        if self.Detach and not Utils.IsWindows():
            Cprint(">>>/detach is redundant on non-windows systems", level=1)

        return True

    def _getOrInitExternalModule(self, path: str) -> ExternalModule:
        if path in self.ExternalModules:
            return self.ExternalModules[path]
        else:
            if os.path.isabs(path):
                module = ExternalModule(path)
            elif os.path.isfile(relative := os.path.join(os.path.split(__file__)[0], "go_modules", path)):
                module = ExternalModule(relative)
            else:
                module = ExternalModule(path)
            module.Init(self)
            self.ExternalModules[path] = module
            return module

    def ProcessApplyArguments(self, targetArguments: typing.List[str]) \
            -> typing.Optional[typing.List[typing.Union[typing.List[str], Utils.RepeatGenerator]]]:
        newArguments = []

        # region preprocess inline markers and apply list usage

        unresolvedMarkers = []

        if self.NoInline:
            newArguments = list(targetArguments)
        else:
            for argument in targetArguments:
                markers = InlineMarkerSpecifier.TryParseMarkers(argument)
                if markers is None:
                    newArguments.append(argument)
                    continue

                notEmpty = list()
                for item in markers:
                    if isinstance(item, str):
                        if len(item) > 0:
                            notEmpty.append(item)
                    elif isinstance(item, InlineMarkerSpecifier):
                        if item.Index is None:
                            item.applyList = None
                            unresolvedMarkers.append(item)
                        else:
                            item.ApplyList = self.ApplyLists[item.Index]
                            item.ApplyList.Used = True

                        notEmpty.append(item)
                    else:
                        item.Modifiers = [x for x in item.Modifiers if x[0] != "i"]
                        self.ApplyLists.append(item)
                        marker = InlineMarkerSpecifier(len(self.ApplyLists) - 1)
                        marker.ApplyList = item
                        item.Used = True

                        notEmpty.append(item)

                newArguments.append(notEmpty[0] if len(notEmpty) == 1 else notEmpty)

        unusedListQueue = queue.SimpleQueue()
        for i in range(len(self.ApplyLists)):
            applyList = self.ApplyLists[i]
            if any(x[0] == "i" for x in applyList.Modifiers):
                applyList.Used = True
                for modifier in applyList.Modifiers:
                    if modifier[0] == "i":
                        marker = InlineMarkerSpecifier(i)
                        marker.ApplyList = applyList
                        newArguments.insert(modifier[1], marker)
            elif not applyList.Used:
                if not any(x[0] == "d" for x in applyList.Modifiers):
                    unusedListQueue.put((i, applyList))

        sequentialIndex = 0
        for marker in unresolvedMarkers:
            if unusedListQueue.empty():
                i = sequentialIndex
                nextList = self.ApplyLists[sequentialIndex]
                sequentialIndex += 1
                if sequentialIndex >= len(self.ApplyLists):
                    sequentialIndex = 0
            else:
                (i, nextList) = unusedListQueue.get()

            marker.Index = i
            marker.ApplyList = nextList
            nextList.Used = True

        while not unusedListQueue.empty():
            (i, applyList) = unusedListQueue.get()
            marker = InlineMarkerSpecifier(i)
            marker.ApplyList = applyList
            applyList.Used = True

            newArguments.append(marker)

        # endregion

        if len(self.ApplyLists) == 0:
            repeat = 1 if self.RepeatCount is None else self.RepeatCount
            return [Utils.RepeatGenerator(x, repeat) for x in targetArguments]

        # region generate lists

        duplicatesToDo = []
        usesToDo = []

        for i in range(len(self.ApplyLists)):
            applyArgument = self.ApplyLists[i]

            if applyArgument.SourceType == "c":
                applyArgument.List = [x for x in Utils.GetClipboardText().splitlines() if len(x) > 0]
            elif applyArgument.SourceType == "d":
                # processed right after every other list
                duplicate = (self.ApplyLists[int(applyArgument.Source)], applyArgument)
                duplicatesToDo.append(duplicate)
            elif applyArgument.SourceType == "f":
                applyArgument.List = Utils.ReadAllLines(applyArgument.Source)
            elif applyArgument.SourceType == "g":
                applyArgument.List = Utils.CaptureGoOutput(applyArgument.Source)
            elif applyArgument.SourceType == "h":
                applyArgument.List = Utils.GetTextFromUrl(applyArgument.Source).splitlines()
            elif applyArgument.SourceType == "i":
                applyArgument.List = applyArgument.Source.split(",")
            elif applyArgument.SourceType == "p":
                applyArgument.List = Utils.ReadStdin()
            elif applyArgument.SourceType == "py":
                pyapplyArguments = applyArgument.Source.split(",", 1)
                modulePath = pyapplyArguments[0]
                moduleArgument = None
                if len(pyapplyArguments) == 2:
                    moduleArgument = pyapplyArguments[1]
                applyArgument.List = self._getOrInitExternalModule(modulePath).GetApplyList(applyArgument, moduleArgument)
            elif applyArgument.SourceType == "r":
                rangeArgumentsRegex = re.compile("-?\\d+(,-?\\d+){0,2}", re.I)
                if rangeArgumentsRegex.match(applyArgument.Source):
                    applyArgument.List = [str(x) for x in eval("range(" + applyArgument.Source + ")")]
            elif applyArgument.SourceType == "u":
                # processed after all modifiers
                reuse = (self.ApplyLists[int(applyArgument.Source)], applyArgument)
                duplicatesToDo.append(reuse)
                usesToDo.append(reuse)

            if applyArgument.SourceType not in {"d", "u"} and not applyArgument.List:
                Cprint(">>>apply list index %d is empty! exiting with failure... (%s)" % (i, applyArgument.SourceText), level=3)
                return None

        for (sourceList, destList) in duplicatesToDo:
            destList.List = list(sourceList.List)
        for (sourceList, destList) in usesToDo:
            destList.Modifiers = [*sourceList.Modifiers, *destList.Modifiers]

        # endregion

        # region process modifiers

        for applyArgument in self.ApplyLists:
            for (modifierType, modifierArgument) in applyArgument.Modifiers:
                if modifierType == "d":
                    # already processed
                    pass
                elif modifierType == "e":
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
                    applyArgument.List = [modifierArgument.join(applyArgument.List)]
                elif modifierType == "g":
                    applyArgument.List = Utils.CaptureGoOutput(modifierArgument, applyArgument.List)
                elif modifierType == "py":
                    (modulePath, moduleArgument) = modifierArgument
                    applyArgument.List = self._getOrInitExternalModule(modulePath).ModifyApplyList(applyArgument, applyArgument.List, moduleArgument)
                elif modifierType == "rep":
                    (x, y) = modifierArgument
                    applyArgument.List = [t.replace(x, y) for t in applyArgument.List]
                elif modifierType == "rm":
                    regex = re.compile(modifierArgument, re.I)
                    applyArgument.List = [x for x in applyArgument.List if regex.search(x)]
                elif modifierType == "rs":
                    (groupNumber, regexString) = modifierArgument
                    regex = re.compile(regexString, re.I)
                    for i in range(len(applyArgument.List)):
                        match = regex.search(applyArgument.List[i])
                        if match:
                            groups = match.groups()
                            if groupNumber <= regex.groups:
                                applyArgument.List[i] = groups[groupNumber - 1]
                            else:
                                applyArgument.List[i] = match.group(0) # entire match
                        else:
                            applyArgument.List[i] = ""
                elif modifierType == "s":
                    (excludeInstead, expression) = modifierArgument
                    slices = []
                    for expr in expression.split(","):
                        s = Utils.GetSliceFunc(expr)
                        if s:
                            slices.append(s)
                    applyArgument.List = Utils.ApplySlices(slices, applyArgument.List, excludeInstead)
                elif modifierType == "sp":
                    pattern = modifierArgument
                    newList = [re.split(pattern, x) for x in applyArgument.List]
                    applyArgument.List = [x for l in newList for x in l if len(x) > 0]
                elif modifierType == "ss":
                    s = Utils.GetSliceFunc(modifierArgument)
                    applyArgument.List = [s(x) for x in applyArgument.List]
                elif modifierType == "strip":
                    side, characters = modifierArgument
                    side = (side or "").lower()
                    if side == "l":
                        stripper = str.lstrip
                    elif side == "r":
                        stripper = str.rstrip
                    else:
                        stripper = str.strip
                    applyArgument.List = [stripper(x, characters) for x in applyArgument.List]
                elif modifierType == "tsp":
                    applyArgument.List = [applyArgument.List]
                elif modifierType == "w":
                    (inverted, pattern) = modifierArgument
                    applyArgument.List = [x for x in applyArgument.List if fnmatch.fnmatch(x, pattern) is not inverted] # big brain inversion (== xor (== is not))
                elif modifierType == "xtr":
                    (groupNumber, pattern) = modifierArgument
                    regex = re.compile(pattern, re.I)
                    newList = []
                    for i in applyArgument.List:
                        newList.append(regex.findall(i))
                    applyArgument.List = [x for l in newList for x in l]

        # endregion

        # region calculate and adjust lengths

        # todo transposed lists behave unexpectedly

        if self.RepeatCount is not None and self.RepeatCount >= 2:
            for applyArgument in self.ApplyLists:
                if applyArgument.ShouldTranspose:
                    continue
                originalLength = len(applyArgument.List)

                for i in range(self.RepeatCount - 1):
                    applyArgument.List.extend(applyArgument.List[:originalLength])

        if self.Rollover:
            maxOriginalLength = max(len(x.List) for x in self.ApplyLists)

            for applyArgument in self.ApplyLists:
                if applyArgument.ShouldTranspose:
                    continue
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

        try:
            minLength = min(len(x.List) for x in self.ApplyLists if not x.ShouldTranspose)
        except:
            minLength = self.RepeatCount or 1

        for applyArgument in self.ApplyLists:
            if len(applyArgument.List) > minLength:
                applyArgument.List = applyArgument.List[:minLength]

        # endregion

        # region expand and flatten/transpose lists

        finalApplyLength = 1 if len(self.ApplyLists) == 0 else len(self.ApplyLists[0].List)

        def resolveSpecifier(item: typing.Union[InlineMarkerSpecifier, ApplyListSpecifier]) -> typing.List[str]:
            if isinstance(item, InlineMarkerSpecifier):
                return item.ApplyList.List
            elif isinstance(item, ApplyListSpecifier):
                return item.List

        def simplifyList(arguments: list) -> list:
            relevantArguments = list()
            for item in arguments:
                if isinstance(item, str):
                    if len(item) > 0:
                        relevantArguments.append(item)
                else:
                    relevantArguments.append(item)
            return relevantArguments

        # todo: this shit to semi-recursive (but still shit)
        i = 0
        while i < len(newArguments):
            argument = newArguments[i]

            if isinstance(argument, str):
                result = Utils.RepeatGenerator(argument, finalApplyLength)
            elif isinstance(argument, InlineMarkerSpecifier) or isinstance(argument, ApplyListSpecifier):
                result = resolveSpecifier(argument)

                if argument.ShouldTranspose:
                    del newArguments[i]
                    Utils.InsertMany(newArguments, i, (Utils.RepeatGenerator(x, finalApplyLength) for x in result[0]))
                    i += len(result[0])
                    continue
            else:
                argument = simplifyList(argument)

                j = 0
                while j < len(argument):
                    arg = argument[j]

                    if isinstance(arg, str):
                        pass
                    else:
                        args = resolveSpecifier(arg)

                        if arg.ShouldTranspose:
                            argument[j] = Utils.JoinForShell(args[0], False)
                        else:
                            argument[j] = args
                    j += 1

                argument = (Utils.RepeatGenerator(x, finalApplyLength) if isinstance(x, str) else x for x in argument)
                result = list()
                for rejoined in zip(*argument):
                    result.append("".join(rejoined))

            newArguments[i] = result
            i += 1

        # endregion

        return newArguments


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

        Utils.TryInitColorama()

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
                                      args=(dict(run), semaphore, self._PrintArray, self._PrintArrayLock, self._Configuration.Priority))
            threads.append(thread)

            thread.start()

        for thread in threads:
            thread.join()

    @staticmethod
    def _RunInstance(runParameters: dict, doneSemaphore: threading.Semaphore,
                     printList: typing.List, printListLock: threading.Lock,
                     priority: typing.Tuple[int, bool]):
        if "stdout" in runParameters and runParameters["stdout"] == sys.stdout:
            runParameters["stdout"] = subprocess.PIPE
        if "stderr" in runParameters and runParameters["stderr"] == sys.stderr:
            runParameters["stderr"] = subprocess.PIPE

        printIndex = None
        with printListLock:
            printIndex = len(printList)
            printList.append(None)

        with Utils.PriorityModifier(*priority):
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

            Utils.ClearScreen()
            for (i, output) in tempArray:
                print("[{0:3d}]  {1}".format(i + 1, Utils.RemoveControlCharacters(output)))

            print("{0:3d} / {1:3d} done".format(sum(1 if x is None else 0 for x in self._PrintArray),
                                                sum(len(x) for x in self._SubprocessArgs)))

            time.sleep(0.25)


def unique(lst: typing.List[MatchCacheItem], ignoreSymlinkDuplication: bool = True) -> typing.List[MatchCacheItem]:
    temp = {}
    symlinks = []

    for i in range(len(lst)):
        item = lst[i]

        if ignoreSymlinkDuplication and item.linkTarget is not None:
            symlinks.append((i, item))
            continue

        key = (os.path.normcase(os.path.normpath(item.path)), os.path.normcase(item.filename))
        if key in temp:
            continue

        temp[key] = (i, item)

    for (i, item) in symlinks:
        key = (os.path.normcase(os.path.normpath(item.linkTarget)), os.path.normcase(item.filename))
        if key in temp:
            continue
        temp[key] = (i, item)

    asList = list(temp.values())
    asList.sort(key=lambda x: x[0])
    return [item for (i, item) in asList]


def FindMatchesAndAlternatives(config: GoConfig, target: str) -> typing.Tuple[typing.List[str], typing.List[str]]:
    if os.path.abspath(target).lower() == target.lower():
        return ([target], [])

    allFiles: typing.List[MatchCacheItem] = []

    scriptDir = Utils.GetScriptDir()
    cachePath = os.path.join(scriptDir, "go.cache")
    overwriteCache = config.RefreshPathCache and not config.DisablePathCache

    if (config.UsePathCache and not config.DisablePathCache) and not config.RefreshPathCache:
        if os.path.isfile(cachePath):
            success = False
            try:
                with open(cachePath, "rb") as f:
                    matchCache = pickle.load(f)
                    assert isinstance(matchCache, MatchCache) and matchCache.GoodVersion()
                    success = True
            except:
                overwriteCache = True

            if success:
                lastRefresh = matchCache.timestamp
                cachedPaths = matchCache.paths

                if lastRefresh < (time.time() - config.CacheInvalidationTime * 3600):
                    overwriteCache = True
                else:
                    if not config.RefreshPathCache:
                        allFiles.extend(cachedPaths)
        else:
            overwriteCache = True

    if len(allFiles) == 0:
        for (path, filename) in itertools.chain(
                Utils.ParsePathsForFiles(os.environ["PATH"].split(os.pathsep), config.TargetedExtensions, False, config.IncludeAnyExecutables, config.IncludeHidden),
                Utils.ParsePathsForFiles([os.getcwd()], config.TargetedExtensions, False, config.IncludeAnyExecutables, config.IncludeHidden),
                Utils.ParsePathsForFiles(config.TargetedPaths, config.TargetedExtensions, True, config.IncludeAnyExecutables, config.IncludeHidden, config.IgnoredPaths)
        ):
            item = MatchCacheItem(path, filename)
            if os.path.islink(path):
                item.linkTarget = os.path.realpath(path)
            allFiles.append(item)

        allFiles = unique(allFiles, config.IgnoreDuplicateLinks)

    if overwriteCache:
        with open(cachePath, "wb") as f:
            matchCache = MatchCache(time.time(), allFiles)
            pickle.dump(matchCache, f)

    similarities = []
    for item in allFiles:
        passedThrough = True

        for (include, directoryFilter) in config.DirectoryFilter:
            (directory, _) = os.path.split(item.path)
            directory = directory.lower()

            if (include and directoryFilter.lower() not in directory) or \
                    (not include and directoryFilter.lower() in directory):
                passedThrough = False
                break

        if not passedThrough:
            continue

        similarities.append((item.path, Utils.ComparePathAndPattern(item.filename, target, config.FuzzyMatch,
                                                                    config.RegexTargetMatch, config.WildcardTargetMatch)))

    exactMatches = [x[0] for x in similarities if x[1] == 1.0]

    fuzzyMatches = [x for x in similarities if x[1] >= 0.7 and x[1] < 1.0]
    fuzzyMatches = sorted(fuzzyMatches, key=lambda x: x[1], reverse=True)
    fuzzyMatches = fuzzyMatches[:5]
    fuzzyMatches = [x[0] for x in fuzzyMatches]

    return (exactMatches, fuzzyMatches)


def GetDesiredMatch(config: GoConfig, target: str) -> str | None:
    (exactMatches, fuzzyMatches) = FindMatchesAndAlternatives(config, target)

    if len(exactMatches) == 0:
        Cprint(">>>no matches found for \"{0}\"!".format(target), level=2)

        if len(fuzzyMatches) > 0:
            Cprint(">>>did you mean:", level=2)

            for fuzzyMatch in fuzzyMatches:
                (directory, filename) = os.path.split(fuzzyMatch)
                Cprint(">>>    {0:24s} in {1}".format(filename, directory), level=2)

        return None

    nthMatch = config.NthMatch
    if nthMatch is None and config.FirstMatchFromConfig:
        nthMatch = 0

    if len(exactMatches) > 1 and nthMatch is None:
        Cprint(">>>multiple matches found!", level=2)

        for i in range(len(exactMatches)):
            (directory, filename) = os.path.split(exactMatches[i])
            Cprint(">>> [{0:2d}]\t{1:20s}\tin {2}".format(i, filename, directory), level=2)

        return None
    if len(exactMatches) > 1 and config.FirstMatchFromConfig and config.NthMatch is None:
        Cprint(">>>autoselected the first of many matches because of config \"AlwaysFirst\"!")

    if len(exactMatches) > 1 and nthMatch is not None:
        if nthMatch >= len(exactMatches):
            Cprint(">>>nth match index out of range!", level=2)
            return None

        return exactMatches[nthMatch]

    return exactMatches[0]


def echoTarget(target: str, arguments: typing.List[str], unsafe: bool = False):
    print(Utils.JoinForShell([target, *arguments], not unsafe))

def Run(config: GoConfig, goTarget: str,
        targetArguments: typing.List[typing.Union[typing.List[str], Utils.RepeatGenerator]]) \
        -> typing.Optional[int]:
    runs = 1
    if config.RepeatCount is not None and len(targetArguments) == 0:
        runs = config.RepeatCount
    elif len(targetArguments) != 0:
        runs = len(targetArguments[0])

    if runs > 50 and not config.AlwaysYes:
        Cprint(">>>{0} lines present at source. continue? (Y/n)".format(runs), level=2)
        if not sys.stdin.isatty():
            Cprint(">>>stdin is piped. Please use /yes to run", level=2)
            return -1

        answer = ""
        try:
            answer = input()
        except EOFError:
            Cprint(">>>could not read stdin; use /yes to run", level=2)
            return -1

        if len(answer) > 0 and answer[0] != "y":
            return -1

    if config.AsShellScript:
        if Utils.IsWindows():
            target = GetDesiredMatch(config, "cmd.exe")
        else:
            target = GetDesiredMatch(config, "bash")
    elif config.Shell:
        target = goTarget
    else:
        target = GetDesiredMatch(config, goTarget)

    if target is None:
        return -1

    parallelRunner = ParallelRunner(config) if config.Parallel else None
    runMethod = subprocess.run if config.WaitForExit else subprocess.Popen
    stdin = sys.stdin if config.WaitForExit else subprocess.DEVNULL
    stdout = sys.stdout if config.WaitForExit else subprocess.DEVNULL
    stderr = sys.stderr if config.WaitForExit else subprocess.DEVNULL
    flags = 0
    asscriptArguments = []

    if Utils.IsWindows():
        if not config.WaitForExit:
            flags |= subprocess.CREATE_NEW_PROCESS_GROUP
        if config.Detach:
            flags |= subprocess.DETACHED_PROCESS
    else:
        # none of the previous flags are needed
        pass

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

    echoedActualTarget = target if not config.AsShellScript else goTarget

    shouldEchoAlways = config.EchoTarget and config.EchoWhen == EchoWhenValues.Always and can_print(1)
    shouldEchoSuccess = config.EchoTarget and config.EchoWhen == EchoWhenValues.Success and can_print(2)
    shouldEchoFail = config.EchoTarget and config.EchoWhen == EchoWhenValues.Failure and can_print(2)

    for arguments in (zip(*targetArguments) if len(targetArguments) > 0 else [[]]):
        if shouldEchoAlways:
            echoTarget(echoedActualTarget, arguments, config.Unsafe)
        if config.DryRun:
            continue
        if config.AsShellScript:
            asscriptArguments.append([goTarget] + list(arguments))
            continue

        runArgument = [target, *arguments]
        if config.Unsafe:
            runArgument = Utils.JoinForShell(runArgument, False)

        subprocessArgs = {"args": runArgument, "shell": config.Shell, "cwd": directory, "creationflags": flags,
                          "stdin": stdin, "stdout": stdout, "stderr": stderr, "start_new_session": not config.WaitForExit}

        if config.Parallel:
            parallelRunner.EnqueueRun(subprocessArgs)
        else:
            with Utils.PriorityModifier(*config.Priority):
                process = runMethod(**subprocessArgs)
            if config.WaitForExit:
                returnCode = process.returncode
                if (returnCode == 0 and shouldEchoSuccess) or (returnCode != 0 and shouldEchoFail):
                    echoTarget(echoedActualTarget, arguments, config.Unsafe)
                if runs == 1:
                    return returnCode

    if config.PrintTarget:
        print(target)
    if config.DryRun:
        return 0

    if config.Parallel:
        parallelRunner.Start()
    if config.AsShellScript:
        tempscriptPath = Utils.CreateScriptFile(asscriptArguments, config.EchoOff, config.Unsafe)
        subprocessArgs = {"args": [tempscriptPath], "shell": True, "cwd": directory, "creationflags": flags,
                          "stdin": stdin, "stdout": stdout, "stderr": stderr, "start_new_session": not config.WaitForExit}
        with Utils.PriorityModifier(*config.Priority):
            process = runMethod(**subprocessArgs)
        if config.WaitForExit:
            return process.returncode

def main():
    global config
    
    if len(sys.argv) == 1:
        PrintHelp()
        return 0

    config = GoConfig()
    args = list(sys.argv)

    if (defaultArgs := os.getenv("GO_DEFAULT_ARGUMENTS")):
        args = [args[0], *shlex.split(defaultArgs), *args[1:]]

    i = 1
    while i < len(args):
        if not config.TryParseArgument(args[i]):
            break
        i += 1

    if i == len(args):
        PrintHelp()
        return 0

    if not config.Validate():
        return -1

    processWaiter = Utils.ProcessWaiter()
    if config.WaitForQueue:
        processWaiter += Utils.ProcessWaiter.FromQueue()
    if config.WaitFor:
        processWaiter += Utils.ProcessWaiter.FromPids(config.WaitFor)

    target = args[i]
    targetArguments = config.ProcessApplyArguments(args[i + 1:])

    if targetArguments is not None:
        with processWaiter:
            result = Run(config, target, targetArguments)
    else:
        result = -1

    for modulePath in config.ExternalModules:
        config.ExternalModules[modulePath].Exit()
    return result or 0


if __name__ == "__main__":
    exit(main())
