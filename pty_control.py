from dataclasses import dataclass

@dataclass
class PtyControl:
    input_processed: bool = False

pty_control = PtyControl(input_processed=False)

