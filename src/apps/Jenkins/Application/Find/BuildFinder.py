from src.apps.Jenkins.Domain.ServerRepository import ServerRepository
from typing import Type

class BuildFinder:
    def __init__(self, repository: Type[ServerRepository], name: str) -> None:
        self.repository = repository
        self.name = name
        self.consoleLines = 0

    def exec(self, number: int) -> str:
        try:
            consoleLines = self.repository.get_build_console_output(self.name, number).split("\n")
        except Exception as e:
            print(f"An error occurred while getting console output: {e}. Continuing execution as non-fatal.")
            consoleLines = []

        consoleLinesCount = len(consoleLines)
        for i in range(self.consoleLines, consoleLinesCount):
            print(consoleLines[i])

        self.consoleLines = consoleLinesCount

        return self.repository.get_status(number)
    
    def number(self) -> int:
        return self.repository.get_number()
