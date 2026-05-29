"""WTT (Windows Test Technology) log report for lit.

Produces .wtl files. WTL is a UTF-16 XML format used by the Windows test framework to report
per-test pass/fail results.
"""

import os
import platform
import time

from xml.sax.saxutils import escape, quoteattr

import lit.Test
from lit.reports import Report


def _timestamp():
    t = time.localtime()
    return "%d:%d:%d %d:%d:%d:%d" % (
        t.tm_year, t.tm_mon, t.tm_mday,
        t.tm_hour, t.tm_min, t.tm_sec, 0
    )


def _sanitize_attr(text):
    """Escape text for use in an XML attribute value."""
    # Replace newlines/tabs with spaces, then use quoteattr for XML escaping.
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    # quoteattr returns the value with surrounding quotes
    return quoteattr(text)


class WttReport(Report):
    def write_results(self, tests, elapsed):
        with open(self.output_file, "w", encoding="utf-16") as f:
            self._write_results_to_file(tests, elapsed, f)

    def _write_results_to_file(self, tests, elapsed, file):
        machine = platform.node()
        pid = os.getpid()
        ts = _timestamp()

        file.write('<?xml version="1.0" encoding="utf-16"?>\n')
        file.write("<WTT-Logger>\n")

        # Runtime info
        file.write(
            '<RTI ID="1" Machine="%s" ProcessName="lit" '
            'ProcessID="%d" ThreadID="0" '
            'BaseTime="%s" Frequency="1" />\n' % (machine, pid, ts)
        )
        file.write('<CTX ID="1" Current="WTTLOG" Parent="ROOT" />\n')

        passed = 0
        failed = 0
        skipped = 0

        for test in tests:
            if test.result is None:
                continue

            code = test.result.code
            name = escape(test.getFullName())

            # Only log tests that actually ran
            if code in (lit.Test.EXCLUDED, lit.Test.SKIPPED, lit.Test.UNSUPPORTED):
                skipped += 1
                continue

            # Map lit result codes to WTT results
            if code in (lit.Test.PASS, lit.Test.XFAIL):
                result = "Pass"
                passed += 1
            else:
                result = "Fail"
                failed += 1

            file.write('<StartTest Title=%s TUID="">\n' % _sanitize_attr(name))
            file.write("</StartTest>\n")

            # Write error output for failures
            if result == "Fail" and test.result.output:
                file.write('<Err UserText=%s>\n' % _sanitize_attr(test.result.output[:4096]))
                file.write("</Err>\n")

            # Write pass messages
            if result == "Pass" and test.result.output:
                file.write('<Msg UserText=%s>\n' % _sanitize_attr(test.result.output[:1024]))
                file.write("</Msg>\n")

            file.write(
                '<EndTest Title=%s TUID="" Result="%s" Repro="">\n'
                % (_sanitize_attr(name), result)
            )
            file.write("</EndTest>\n")

        if skipped > 0:
            file.write(
                '<Msg UserText=%s>\n'
                % _sanitize_attr(
                    "%d test(s) were UNSUPPORTED and excluded from results "
                    "(not in requires group or platform mismatch)." % skipped
                )
            )
            file.write("</Msg>\n")

        total = passed + failed
        file.write(
            '<PFRollup Total="%d" Passed="%d" Failed="%d" '
            'Blocked="0" Warned="0" Skipped="0" />\n'
            % (total, passed, failed)
        )
        file.write("</WTT-Logger>\n")
