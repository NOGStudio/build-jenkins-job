from src.apps.Jenkins.Domain.ServerRepository import ServerRepository
from typing import Type
import time
import jenkins
import re

class BuildFinder:
    def __init__(self, repository: Type[ServerRepository], name: str) -> None:
        self.repository = repository
        self.name = name
        self.consoleLines = 0

    def exec(self, number: int) -> str:
        attempts = 3
        for attempt in range(attempts):
            try:
                console_output = self.repository.get_build_console_output(self.name, number)
                consoleLines = console_output.split("\n")
                consoleLinesCount = len(consoleLines)
                
                for i in range(self.consoleLines, consoleLinesCount):
                    line = consoleLines[i]
                    print(line)
                    self.detect_and_report_issues(line)

                self.consoleLines = consoleLinesCount

                status = self.repository.get_status(number)
                return status
            except jenkins.JenkinsException as e:
                print(f"Attempt {attempt + 1} of {attempts} failed: {e}")
                if attempt >= attempts - 1:
                    print(f"Job [{self.name}] number [{number}] does not exist after {attempts} attempts. Continuing as non-fatal error.")
                    return "UNKNOWN"

    def detect_and_report_issues(self, line: str):
        warning_patterns = [
            re.compile(r'.*Warning:.*'),  
            # Add more patterns as needed
        ]
        
        error_patterns = [
            re.compile(r'.*Error:.*'),  
            # Add more patterns as needed
        ]
        
        for pattern in warning_patterns:
            if pattern.match(line):
                self.report_warning(line)

        for pattern in error_patterns:
            if pattern.match(line):
                self.report_error(line)

    def report_warning(self, message: str):
        print(f"::warning::{message}")

    def report_error(self, message: str):
        print(f"::error::{message}")

    def number(self) -> int:
        return self.repository.get_number()
