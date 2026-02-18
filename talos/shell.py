import asyncio
from dataclasses import dataclass


@dataclass
class Result:
    command: str
    code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.code == 0


async def run(command: str, timeout: float = 120.0, cwd: str | None = None) -> Result:
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return Result(
            command=command,
            code=proc.returncode or 0,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )
    except asyncio.TimeoutError:
        proc.kill()
        return Result(command=command, code=-1, stdout="", stderr="timed out")
    except Exception as e:
        return Result(command=command, code=-1, stdout="", stderr=str(e))
