"""Diagnostics — parse test failures and extract actionable insights."""

import re


class Diagnostics:
    """Analyze test failures to identify root causes.

    Rule-based: no LLM required.
    """

    @staticmethod
    def parse_failure(output: str) -> str:
        """Extract a concise failure summary from pytest output.

        Args:
            output: Combined stdout + stderr from pytest.

        Returns:
            Summary of the failure.
        """
        if not output:
            return "No output to analyze."

        lines = output.split("\n")
        summary_parts: list[str] = []

        # Look for FAILED lines
        failed_lines = [line for line in lines if "FAILED" in line and "::" in line]
        if failed_lines:
            summary_parts.append("Failed tests:")
            summary_parts.extend(f"  {ln.strip()}" for ln in failed_lines[:5])

        # Look for AssertionError
        for i, line in enumerate(lines):
            if "AssertionError" in line:
                summary_parts.append(f"AssertionError: {line.strip()}")
                break
            if "Error" in line and ("Traceback" in (lines[i - 1] if i > 0 else "")):
                summary_parts.append(f"Error: {line.strip()}")
                break

        # Look for test summary
        for line in lines:
            if "passed" in line.lower() or "failed" in line.lower():
                summary_parts.append(line.strip())
                break

        return "\n".join(summary_parts) if summary_parts else "No specific failure pattern detected."

    @staticmethod
    def extract_error_summary(output: str) -> str:
        """Extract the last error block from output."""
        if not output:
            return ""
        # Try to find the last traceback-like block
        lines = output.split("\n")
        for i in range(len(lines) - 1, -1, -1):
            if "Error" in lines[i] or "FAIL" in lines[i]:
                start = max(0, i - 5)
                return "\n".join(lines[start:i + 3])
        return output[-500:]

    @staticmethod
    def identify_likely_files(output: str) -> list[str]:
        """Extract file paths from error output."""
        files: set[str] = set()
        for match in re.finditer(r'File "([^"]+)"', output):
            files.add(match.group(1))
        for match in re.finditer(r"(\S+\.py)[:\s]", output):
            files.add(match.group(1))
        return sorted(files)

    @staticmethod
    def parse_structured(output: str) -> dict:
        """Parse test failure into a structured dict.

        Returns keys: error_type, error_message, failing_file,
        failing_line, failing_test, traceback_summary.
        """
        result = {"error_type": "", "error_message": "", "failing_file": "",
                   "failing_line": "", "failing_test": "", "traceback_summary": ""}
        if not output:
            return result
        lines = output.split("\n")

        # Error type
        for line in lines:
            for err in ["ZeroDivisionError", "AssertionError", "ImportError",
                         "TypeError", "FileNotFoundError", "AttributeError",
                         "ValueError", "KeyError", "IndexError", "NameError"]:
                if err in line:
                    result["error_type"] = err
                    result["error_message"] = line.strip()
                    break
            if result["error_type"]:
                break

        # Failing file + line
        for match in re.finditer(r'File "([^"]+)", line (\d+)', output):
            result["failing_file"] = match.group(1)
            result["failing_line"] = match.group(2)

        # Failing test
        for match in re.finditer(r"(\S+::\S+)", output):
            if "ERROR" in match.group(0) or "FAILED" in match.group(0):
                continue
            result["failing_test"] = match.group(1)

        # Traceback summary
        tb_started = False
        tb_lines = []
        for line in lines:
            if "Traceback" in line:
                tb_started = True
            if tb_started:
                tb_lines.append(line)
        result["traceback_summary"] = "\n".join(tb_lines[-10:])
        return result
