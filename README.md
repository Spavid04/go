## What is this thing?
This script started from a simple necessity to run a program, multiple times, with different arguments, on Windows. Other restraints such as a no-external-dependency single-file were optional, but convenient, and they stuck until today (well, except external dependencies 🤭).

As it stands now, go.py is a needlessly large python script that finds an executable, and launches it with some arguments. (on Linux too!)

## Usage
The format for any go call is:

`go [go arguments...] [program name] [target arguments...]`

Most `go` arguments revolve around reading and then processing different arguments for the target program.

In most cases, it shouldn't make any difference if you run a program with `go` prepended to the command line, more or less like prepending `cmd /c`.

**Detailed help is available by running go without any arguments, or `go /help`.**

## Requirements
Most features only require a standard Python 3.8+ interpreter.

However, there are a couple of optional requirements that either enhance or enable other features.

## Examples
```
Run a program:
    go calc

Run a specific program, regardless of it being found or not:
    go C:\NotInPath\ayy.exe

Run a program in its directory:
    go /cd cmd /c dir /b

Temporarily add an extension to the allowed list, and run a program with it:
    go /ext+"bat" batchfile

Fetch all urls listed in a file, with wget:
    go /fapply-"urls.txt" wget

Use a go subcommand as an apply argument:
    go /gapply-"cmd /c dir" cmd /c echo

Explicitly set apply argument position with inline markers:
    go /iapply-"3,4" /iapply-"1,2" cmd /c echo %%1%% %%0%%

Generate all integers between 0 and 100, and format them as a 0 padded 3 digit number:
    go /rapply-1,100+[fi:%03d] cmd /c echo

Print last 4 characters of all files in the current directory, read from stdin:
    dir /b | go /papply+[ss:-4:] cmd /c echo

Print only the extensions of all files in the current directory, read from stdin; not using [^.]+ due to parsing issues:
    dir /b | go /papply+[rs:\..+?$] cmd /c echo

Concatenate files using cmd's copy and go's format+flatten:
    dir /b *.bin | go /asscript /papply+[f:\"%s\"]+[fl:+] copy /b %%%% out.bin
```

## Todo
* sometimes, unicode strings perform jankily, but I am not sure how to fix this
  * for example running `dir /b | go /papply cmd /c echo` in a directory containing files with unicode names
* `/parallel` usually has weird output (but runs properly)

## Note
Most features were tested "by hand" only, and Linux support might be a bit below Windows.

This project has nothing to do with Go (the programming language).
