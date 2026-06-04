"""Code agent example — fix a bug in the toy repo."""

import asyncio
from pathlib import Path

from evoagent.code.agent import CodeAgent

TOY_REPO = Path(__file__).parent / "toy_repo_bug"


async def main():
    agent = CodeAgent(workspace=TOY_REPO, max_iterations=3)
    result = await agent.run("Fix the division-by-zero bug in calculator.py")

    print(f"Success:       {result.success}")
    print(f"Changed files: {result.changed_files}")
    print(f"Iterations:    {result.iterations}")
    print(f"Errors:        {result.errors}")
    if result.test_result:
        print(f"Test exit:     {result.test_result.exit_code}")
    print(f"\nDiff:\n{result.diff}")


if __name__ == "__main__":
    asyncio.run(main())
