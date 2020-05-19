import os
import signal
from pty import openpty
from subprocess import Popen
from time import sleep
from typing import List, Optional, Tuple, Any
from datetime import datetime
from io import TextIOWrapper
from threading import Thread
from select import select


def studSaveStrComp(ref: str, other: str, strip: bool = True, ignoreCase: bool = True, ignoreNonAlNum=True):
    """
    Student save compare between strings.
    Converts both to lower, strips them and removes all non alphanumeric chars
    before comparision.
    """
    # Strip:
    if strip:
        ref = ref.strip()
        other = other.strip()

    # Convert to lower
    if ignoreCase:
        ref = ref.lower()
        other = other.lower()

    # Remove all non alphanumeric chars:
    if ignoreNonAlNum:
        ref = "".join(c for c in ref if c.isalnum())
        other = "".join(c for c in other if c.isalnum())

    # print("Ref: {}\nOther:{}".format(ref, other))
    return ref == other


# Limit for stdout in chars.
# Should prevent to much output on artemis if for example there is a loop in a tree.
__stdoutCharsLeft: int = 15000
# By default the stdout limit is disabled:
__stdoutLimitEnabled: bool = False


def resetStdoutLimit(limit: int = 15000):
    """
    Resets the stout limit to the given limit (default = 15.000 chars).
    """
    global stdoutCharsLeft # Required since we want to modify stdoutCharsLeft
    stdoutCharsLeft = limit


def setStdoutLimitEnabled(enabled: bool):
    """
    Enables or disables the stdout limit.
    Does not restet the chars left!
    """
    global __stdoutLimitEnabled
    __stdoutLimitEnabled = enabled


def __printStdout(text: str):
    """
    Prints the given text to stdout.
    Only if there are still enough chars in stdoutCharsLeft left.
    Else will not print anything.
    """
    global stdoutCharsLeft # Required since we want to modify stdoutCharsLeft

    if not __stdoutLimitEnabled:
        print(text)
    elif stdoutCharsLeft > 0:
        if stdoutCharsLeft >= len(text):
            print(text)
        else:
            print(text[:stdoutCharsLeft] + "...")
        stdoutCharsLeft -= len(text)
        if stdoutCharsLeft <= 0:
            print("[STDOUT LIMIT REACHED]".center(50, "="))


# A cache of all that the tester has been writing to stdout:
testerOutputCache: List[str] = list()


def clearTesterOutputCache():
    """
    Clears the testerOutputCache.
    """
    testerOutputCache.clear()


def getTesterOutput():
    """
    Returns the complete tester output as a single string.
    """
    return "\n".join(testerOutputCache)


def __getCurDateTimeStr():
    """
    Returns the current date and time string (e.g. 11.10.2019_17:02:33)
    """
    return datetime.now().strftime("%d.%m.%Y_%H:%M:%S")


def printTester(text: str, addToCache: bool=True):
    """
    Prints the given string with the '[TESTER]: ' tag in front.
    Should be used instead of print() to make it easier for students
    to determin what came from the tester and what from their programm.
    """
    msg: str = "[{}][TESTER]: {}".format(__getCurDateTimeStr(), text)
    __printStdout(msg)
    if addToCache:
        testerOutputCache.append(msg)


def printProg(text: str, addToCache: bool=True):
    """
    Prints the given string with the '[PROG]: ' tag in front.
    Should be used instead of print() to make it easier for students
    to determin what came from the tester and what from their programm.
    """
    msg: str = "[{}][PROG]: {}".format(__getCurDateTimeStr(), text)
    __printStdout(msg)
    if addToCache:
        testerOutputCache.append(msg)


def shortenText(text: str, maxNumChars: int):
    """
    Shortens the given text to a maximum number of chars.
    If there are more chars than specified in maxNumChars,
    it will append: "\n[And {} chars more...]".
    """

    if len(text) > maxNumChars:
        s: str = "\n[And {} chars more...]".format(len(text) - maxNumChars)
        l: int = maxNumChars - len(s)        
        if l > 0:
            return "{}{}".format(text[:l], s)
        else:
            printTester("Unable to limit output to {} chars! Not enough space.".format(maxNumChars), False)
            return ""
    return text


class ReadCache(Thread):
    """
    Helper class that makes sure we only get one line (seperated by '\n')
    if we read multiple lines at once.
    """
    __cacheList: List[str]
    __cacheFile: TextIOWrapper

    __outFd: int
    __outSlaveFd: int

    def __init__(self, filePath: str):
        Thread.__init__(self)
        self.__cacheList = []
        self.__cacheFile = open(filePath, "w")

        # Emulate a terminal:
        self.__outFd, self.__outSlaveFd = openpty()

        self.start()

    def fileno(self):
        return self.__outFd

    def join(self):
        try:
            os.close(self.__outFd)
        except OSError as e:
            printTester("Closing stdout FD failed with: {}".format(e))
        try:
            os.close(self.__outSlaveFd)
        except OSError as e:
            printTester("Closing stdout slave FD failed with: {}".format(e))
        self.__shouldRun = False
        Thread.join(self)

    @staticmethod
    def __isFdValid(fd: int):
        try:
            os.stat(fd)
        except OSError:
            return False
        return True

    def run(self):
        self.__shouldRun = True
        while self.__shouldRun and self.__isFdValid(self.__outSlaveFd):
            try:
                # Wait with a timeout for self.__outSlaveFd to be ready to read from:
                result: Tuple[List[Any], List[Any], List[Any]] = select([self.__outSlaveFd], list(), list(), 0)
                if self.__outSlaveFd in result[0]:
                    data: bytes = os.read(self.__outSlaveFd, 4096)
                else:
                    # Nothing to read:
                    continue
            except OSError:
                break
            if data is not None:
                dataStr: str = data.decode("ascii", "replace")
                try:
                    self.__cacheFile.write(dataStr)
                except UnicodeEncodeError:
                    printTester("Invalid ASCII character read. Skipping line...")
                    continue
                self.__cacheFile.flush()
                self.__cache(dataStr)
                printProg(dataStr)

    def canReadLine(self):
        return len(self.__cacheList) > 0

    def __cache(self, data: str):
        self.__cacheList.extend(data.splitlines(True))

    def readLine(self):
        if self.canReadLine():
            return self.__cacheList.pop(0)
        return ""


class PWrap:
    """
    A wrapper for "Popen".
    """

    cmd: List[str]
    prog: Optional[Popen]
    cwd: Optional[str]

    __stdinFd: int
    __stdinMasterFd: int

    __stdOutLineCache: ReadCache
    __stdErrLineCache: ReadCache
    
    __terminatedTime: Optional[datetime]

    def __init__(self, cmd: List[str], stdoutFilePath: str = "/tmp/stdout.txt", stderrFilePath: str = "/tmp/stderr.txt",
                 cwd: Optional[str] = None):
        self.cmd = cmd
        self.prog = None
        self.cwd: Optional[str] = cwd
        self.stdout = open(stdoutFilePath, "wb")
        self.stderr = open(stderrFilePath, "wb")

        self.__stdOutLineCache = ReadCache(stdoutFilePath)
        self.__stdErrLineCache = ReadCache(stderrFilePath)
        
        self.__terminatedTime = None

    def __del__(self):
        try:
            os.close(self.__stdinFd)
        except OSError as e:
            printTester("Closing stdin FD failed with: {}".format(e))
        try:
            os.close(self.__stdinMasterFd)
        except OSError as e:
            printTester("Closing stdin master FD failed with: {}".format(e))

    def start(self):
        """
        Starts the process and sets all file descriptors to nonblocking.
        """
        # Emulate a terminal for stdin:
        self.__stdinMasterFd, self.__stdinFd = openpty()

        # Start the actual process:
        self.prog = Popen(self.cmd,
                          stdout=self.__stdOutLineCache.fileno(),
                          stdin=self.__stdinMasterFd,
                          stderr=self.__stdErrLineCache.fileno(),
                          universal_newlines=True,
                          cwd=self.cwd,
                          preexec_fn=os.setsid)  # Make sure we store the process group id

    def __readLine(self, lineCache: ReadCache, blocking: bool):
        """
        Reads a single line from the given ReadCache and returns it.

        ---

        blocking:
            When set to True will only return if the process terminated or we read a non empty string.
        """
        while blocking:
            if not lineCache.canReadLine():
                sleep(0.1)
            else:
                line: str = lineCache.readLine()
                return line

    def readLineStdout(self, blocking: bool = True):
        """
        Reads a single line from the processes stdout and returns it.

        ---

        blocking:
            When set to True will only return if the process terminated or we read a non empty string.
        """
        return self.__readLine(self.__stdOutLineCache, blocking)

    def canReadLineStdout(self):
        """
        Returns whether there is a line from the processes stdout that can be read.
        """
        return self.__stdOutLineCache.canReadLine()

    def readLineStderr(self, blocking: bool = True):
        """
        Reads a single line from the processes stderr and returns it.

        ---

        blocking:
            When set to True will only return if the process terminated or we read a non empty string.
        """
        return self.__readLine(self.__stdErrLineCache, blocking)

    def canReadLineStderr(self):
        """
        Returns whether there is a line from the processes stderr that can be read.
        """
        return self.__stdErrLineCache.canReadLine()

    def writeStdin(self, data: str):
        """
        Writes the given data string to the processes stdin.
        """
        os.write(self.__stdinFd, data.encode())
        printTester("Wrote: {}".format(data))

    def hasTerminated(self):
        """
        Returns whether the process has terminated.
        """
        if self.prog is None:
            return True
        
        # Make sure we wait 0.25 seconds after the process has terminated to
        # make sure all the output arrived:
        elif self.prog.poll() is not None:
            if self.__terminatedTime:
                if (datetime.now() - self.__terminatedTime).total_seconds() > 0.25:
                    return True 
            else:
                self.__terminatedTime = datetime.now()
        return False

    def getReturnCode(self):
        """
        Returns the returncode of the terminated process else None.
        """
        return self.prog.returncode

    def waitUntilTerminationReading(self, secs: float = -1):
        """
        Waits until termination of the process and tries to read until either
        the process terminated or the timeout occurred.

        Returns True if the process terminated before the timeout occurred,
        else False.

        ---

        secs:
            The timeout in seconds. Values < 0 result in infinity.
        """
        start: datetime = datetime.now()
        while True:
            if self.hasTerminated():
                return True
            elif 0 <= secs <= (datetime.now() - start).total_seconds():
                return False
            self.readLineStdout(False)
            sleep(0.1)

    def kill(self, signal: int = signal.SIGKILL):
        """
        Sends the given signal to the complet process group started by the process.

        Returns True if the process existed and had to be killed. Else False.

        ---

        signal:
            The signal that should be sent to the process group started by the process.
        """
        # Send a signal to the complete process group:
        try:
            os.killpg(os.getpgid(self.prog.pid), signal)
            return True
        except ProcessLookupError:
            printTester("No need to kill process. Process does not exist any more.")
        return False

    def cleanup(self):
        """
        Should be called once the execution has terminated.
        Will join the stdout and stderr reader threads.
        """

        self.__stdOutLineCache.join()
        self.__stdErrLineCache.join()

    def getPID(self):
        return self.prog.pid
