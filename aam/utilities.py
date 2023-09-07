from dataclasses import dataclass


@dataclass
class Result:
    success: bool
    response: str
