import asyncio


ALLOWED_SERVICES = {
    "neron-core": "neron-core.service",
    "neron-llm": "neron-llm.service",
    "neron-doctor": "neron-doctor.service",
    "neron-cognitive-loop": "neron-cognitive-loop.service",
}


class JournalTool:
    async def execute(self, payload: dict):
        service = payload.get("service")
        lines = int(payload.get("lines", 50))

        if service not in ALLOWED_SERVICES:
            raise ValueError(f"Service non autorisé : {service}")

        lines = max(1, min(lines, 500))
        unit = ALLOWED_SERVICES[service]

        process = await asyncio.create_subprocess_exec(
            "journalctl",
            "-u",
            unit,
            "-n",
            str(lines),
            "--no-pager",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        return {
            "service": service,
            "unit": unit,
            "lines": lines,
            "returncode": process.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
        }
