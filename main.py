#!/usr/bin/env python3

import argparse

import testsuites.intro as intro

from testsuites import Testsuite
from typing import Dict, Any, List

__TESTSUITES: List[Testsuite] = [
	intro.instance
]

__SUITENAMES: List[str] = [t.name() for t in __TESTSUITES]

__SELECTOR: Dict[str, Testsuite] = dict(zip(__SUITENAMES, __TESTSUITES))

def __args() -> Dict[str, Any]:
	parser = argparse.ArgumentParser()

	parser.add_argument("--executable-path", help = "path to the executable file to be tested", type = str, required = True)
	parser.add_argument("--suite", help = "test set selection", type = str, required = True, choices = __SELECTOR)
	parser.add_argument("--timeout-factor", help = "maximum program execution time multiplier (default: 1.0)", type = float, default = 1.0)

	parser.add_argument("--report-output-path", help = "path to the generated JSON report with the specified file name (default: no generation)", type = str, default = None)

	return vars(parser.parse_args())

def __main():
	args = __args()

	executable_path = str(args["executable_path"])
	suite = str(args["suite"])
	timeout_factor = float(args["timeout_factor"])

	report_output_path = args["report_output_path"]

	testsuite = __SELECTOR[suite]
	tester = testsuite.get_tester()

	tester.warm(executable_path, timeout_factor)
	result = tester.run(executable_path, timeout_factor)

	if report_output_path is not None:
		coefficients = testsuite.get_coefficients()
		result.export_report(str(report_output_path), coefficients)

	exit(result.exitcode())

if __name__ == "__main__":
	__main()
