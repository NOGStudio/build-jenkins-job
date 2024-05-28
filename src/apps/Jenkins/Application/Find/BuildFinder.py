from src.apps.Jenkins.Domain.ServerRepository import ServerRepository
from typing import Type
import time
import jenkins

class BuildFinder:
    def __init__(self, repository: Type[ServerRepository], name: str) -> None:
        self.repository = repository
        self.name = name
        self.consoleLines = 0

    def exec(self, number: int) -> str:
        attempts = 3
        for attempt in range(attempts):
            try:
                consoleLines = self.repository.get_build_console_output(self.name, number).split("\n")
                consoleLinesCount = len(consoleLines)
                for i in range(self.consoleLines, consoleLinesCount):
                    print(consoleLines[i])
                self.consoleLines = consoleLinesCount

                status = self.repository.get_status(number)
                return status
            except jenkins.JenkinsException as e:
                print(f"Attempt {attempt + 1} of {attempts} failed: {e}")
                if attempt < attempts - 1:
                else:
                    print(f"Job [{self.name}] number [{number}] does not exist after {attempts} attempts. Continuing as non-fatal error.")
                    return "UNKNOWN"

    def number(self) -> int:
        return self.repository.get_number()
