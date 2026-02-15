import os
import subprocess
import time
import json
import enum

from typing import List, Optional, Tuple, Union, Callable, TypeVar, Any, Dict, Set, Iterable
from abc import abstractmethod, ABC

T = TypeVar('T')

def escape(s: str) -> str:
	escaped = ""
	for c in s:
		if c == "\n":
			escaped += "\\n"
		elif c == "\r":
			escaped += "\\r"
		elif c == "\t":
			escaped += "\\t"
		else:
			escaped += c
	return escaped

class Log:
	def __init__(self, indent_factor: int, indent_n: Optional[int] = None, indent_char: str = " "):
		self.__indent_factor = indent_factor
		self.__indent_n = indent_factor if indent_n is None else indent_n
		self.__indent_char = indent_char

	def scope(self, name: str, action: Callable[[], T]) -> T:
		self.println(name)
		self.__indent_n += self.__indent_factor
		try:
			return action()
		finally:
			self.__indent_n -= self.__indent_factor

	def println(self, line: str):
		print(f"{self.__indent()}{line}")

	def __indent(self) -> str:
		return self.__indent_char * self.__indent_n

class VerdictErrno(enum.Enum):
	ERROR_SUCCESS = "success"
	ERROR_RETURNCODE = "program returns wrong returncode"
	ERROR_ASSERTION = "assertion"
	ERROR_TIMEOUT = "timeout expired"
	ERROR_STDERR_EMPTY = "standard error output is empty"
	ERROR_STDERR_IS_NOT_EMPTY = "standard error output is not empty"
	ERROR_TYPE_ERROR = "type error"
	ERROR_INVALID_FORMAT = "invalid format"

class Verdict:
	def __init__(self, verdict_errno: VerdictErrno, what: Optional[str] = None, extended_what: Union[List[str], str] = [], extended_what_is_hint: bool = False):
		self.__verdict_errno = verdict_errno
		self.__what = what
		self.__extended_what = extended_what.splitlines() if isinstance(extended_what, str) else extended_what
		self.__extended_what_is_hint = extended_what_is_hint

	def errno(self) -> VerdictErrno:
		return self.__verdict_errno

	def is_success(self) -> bool:
		return self.__verdict_errno == VerdictErrno.ERROR_SUCCESS

	def is_failed(self) -> bool:
		return not self.is_success()

	def verdict_message(self) -> str:
		return self.__verdict_errno.value

	def extended_what(self) -> List[str]:
		return self.__extended_what

	def extended_what_is_hint(self) -> bool:
		return self.__extended_what_is_hint

	def what(self) -> str:
		if self.__what is None:
			return "no additional information"
		return self.__what

def ok() -> Verdict:
	return Verdict(VerdictErrno.ERROR_SUCCESS)

class Runned:
	def __init__(self, c_returncode: int, c_stdout: str, c_stderr: str, c_start: int, c_end: int):
		self.__c_returncode = c_returncode
		self.__c_stdout = c_stdout
		self.__c_stderr = c_stderr
		self.__c_start = c_start
		self.__c_end = c_end

	def get_returncode(self) -> int:
		return self.__c_returncode

	def get_stdout(self) -> str:
		return self.__c_stdout

	def get_stderr(self) -> str:
		return self.__c_stderr

	def start(self) -> int:
		return self.__c_start

	def end(self) -> int:
		return self.__c_end

def now() -> int:
	return time.time_ns() // 1000000

class ReturnCodePolicy(enum.Enum):
	MatchIfPresented = 0
	ShouldBeZero = 1
	ShouldNotBeZero = 2

class Run:
	def __init__(self, c_timeout: Union[float, int], c_stdin: Optional[str], c_args: Optional[List[str]], t_returncode_policy: ReturnCodePolicy, t_returncode: Optional[int] = None, t_stdout: Optional[str] = None, t_stderr_empty: bool = True):
		self.__c_timeout = float(c_timeout)
		self.__c_stdin = c_stdin
		self.__c_args = c_args
		self.__t_returncode_policy = t_returncode_policy
		self.__t_returncode = t_returncode
		self.__t_stdout = t_stdout
		self.__t_stderr_empty = t_stderr_empty

	def get_timeout(self) -> float:
		return self.__c_timeout

	def stdin_presented(self) -> bool:
		return self.__c_stdin is not None

	def get_stdin(self) -> str:
		assert self.__c_stdin is not None
		return self.__c_stdin

	def args_presented(self) -> bool:
		return self.__c_args is not None

	def get_args(self) -> List[str]:
		assert self.__c_args is not None
		return self.__c_args

	def expected_returncode_policy(self) -> ReturnCodePolicy:
		return self.__t_returncode_policy

	def expected_returncode_presented(self) -> bool:
		return self.__t_returncode is not None

	def get_expected_returncode(self) -> int:
		assert self.__t_returncode is not None
		return self.__t_returncode

	def expected_stdout_presented(self) -> bool:
		return self.__t_stdout is not None
	
	def get_expected_stdout(self) -> str:
		assert self.__t_stdout is not None
		return self.__t_stdout

	def is_stderr_should_be_empty(self) -> bool:
		return self.__t_stderr_empty

	def run(self, executable_path: str, timeout_factor: float) -> Optional[Runned]:
		cmd = [os.path.abspath(executable_path)]

		if self.args_presented():
			cmd += self.get_args()

		child = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, universal_newlines = True)
		start = now()
		try:
			stdout, stderr = child.communicate(input = self.__c_stdin, timeout = self.__c_timeout * timeout_factor)
			end = now()
			return Runned(child.returncode, stdout, stderr, start, end)
		except subprocess.TimeoutExpired:
			child.kill()

		return None

class Expected(ABC):
	def __init__(self):
		pass

	@abstractmethod
	def test(self, run: Run, runned: Runned) -> Verdict:
		raise NotImplementedError("Expected::test is not implemented")

SingleTest = Tuple[Run, Optional[Expected]]

class Test:
	def __init__(self, name: str, categories: Iterable[str] = [], sequence: List[SingleTest] = []):
		self.__name = name
		self.__categories = set(categories)
		self.__sequence = sequence

	def runs(self) -> List[SingleTest]:
		return self.__sequence

	def name(self) -> str:
		return self.__name

	def add(self, run: Run, expected: Optional[Expected] = None):
		self.add_single_test((run, expected))

	def add_single_test(self, single_test: SingleTest):
		self.__sequence.append(single_test)

	def categories(self) -> Set[str]:
		return self.__categories

	def __pretest(self, run: Run, runned: Runned) -> Verdict:
		stderr_should_be_empty = run.is_stderr_should_be_empty()
		c_stderr = runned.get_stderr()
		is_empty_stderr = c_stderr == ""

		if stderr_should_be_empty and not is_empty_stderr:
			return Verdict(VerdictErrno.ERROR_STDERR_IS_NOT_EMPTY, f"below is what was in the stderr", c_stderr)

		if not stderr_should_be_empty and is_empty_stderr:
			return Verdict(VerdictErrno.ERROR_STDERR_EMPTY)

		policy = run.expected_returncode_policy()
		actual_returncode = runned.get_returncode()

		if policy == ReturnCodePolicy.ShouldBeZero:
			if actual_returncode != 0:
				return Verdict(VerdictErrno.ERROR_RETURNCODE, f"expected {0}, but actual is {actual_returncode}")
		elif policy == ReturnCodePolicy.ShouldNotBeZero:
			if actual_returncode == 0:
				return Verdict(VerdictErrno.ERROR_RETURNCODE, f"expected non-zero returncode, but actual is {actual_returncode}")
		elif policy == ReturnCodePolicy.MatchIfPresented and run.expected_returncode_presented():
			expected_returncode = run.get_expected_returncode()
			if actual_returncode != expected_returncode:
				return Verdict(VerdictErrno.ERROR_RETURNCODE, f"expected {expected_returncode}, but actual is {actual_returncode}")

		return ok()

	def __base_message(self, i: int) -> str:
		return f"Run #{i + 1}/{len(self.__sequence)}..."

	def __print_verdict(self, i: int, verdict: Verdict, log: Log):
		log.println(f"{self.__base_message(i)} FAILED.")
		log.println(f"{verdict.verdict_message().capitalize()}: {verdict.what()}.")
		lines = verdict.extended_what()
		if verdict.extended_what_is_hint():
			assert len(lines) == 1
			log.println(f"Hint: {lines[0]}.")
		elif len(lines) >= 1:
			for line in lines:
				log.println(line)

	def __invoke(self, executable_path: str, timeout_factor: float, log: Log) -> Verdict:
		for i, (run, expected) in enumerate(self.__sequence):
			log.println(self.__base_message(i))

			runned = run.run(executable_path, timeout_factor)

			if runned is None:
				verdict = Verdict(VerdictErrno.ERROR_TIMEOUT, f"executed in more than {run.get_timeout() * timeout_factor}s")
				self.__print_verdict(i, verdict, log)
				return verdict

			verdict = self.__pretest(run, runned)

			if verdict.is_failed():
				self.__print_verdict(i, verdict, log)
				return verdict

			if expected is not None:
				verdict = expected.test(run, runned)
				if verdict.is_failed():
					self.__print_verdict(i, verdict, log)
					return verdict

			log.println(f"{self.__base_message(i)} ok: passed in {runned.end() - runned.start()}ms.")

		return ok()

	def invoke(self, executable_path: str, timeout_factor: float, log: Log) -> Verdict:
		return log.scope(f"Running sequence of {len(self.__sequence)} runs:", lambda : self.__invoke(executable_path, timeout_factor, log))

	def warm(self, executable_path: str, timeout_factor: float):
		for run, _ in self.__sequence:
			_ = run.run(executable_path, timeout_factor)

class Result:
	def __init__(self, tests: List[Test]):
		self.__tests = tests
		self.__verdicts: List[Verdict] = []
		self.__passed = 0

	def add(self, verdict: Verdict):
		if verdict.is_success():
			self.__passed += 1
		self.__verdicts.append(verdict)

	def n(self) -> int:
		return len(self.__verdicts)

	def passed(self) -> int:
		return self.__passed

	def exitcode(self) -> int:
		return 0 if self.n() == self.passed() else 1

	def __get_passed_by_category(self, category: str) -> int:
		passed = 0

		for test, verdict in zip(self.__tests, self.__verdicts):
			if verdict.is_success() and category in test.categories():
				passed += 1

		return passed

	def __get_total_by_category(self, category: str) -> int:
		total = 0

		for test, verdict in zip(self.__tests, self.__verdicts):
			if category in test.categories():
				total += 1

		return total

	def __get_result_by_category(self, category: str) -> float:
		total = self.__get_total_by_category(category)
		passed = self.__get_passed_by_category(category)
		return passed / total

	def __calculate_total(self, coefficients: Dict[str, float]) -> float:
		total = 0.0

		for category, coefficient in coefficients.items():
			result = self.__get_result_by_category(category)
			total += result * coefficient

		return total

	def __get_results_by_categories(self, categories: Iterable[str]) -> Dict[str, float]:
		results: Dict[str, float] = {}

		for category in categories:
			results[category] = self.__get_result_by_category(category)

		return results

	def __get_results(self) -> List[Dict[str, Any]]:
		results: List[Dict[str, Any]] = []

		for i, (test, verdict) in enumerate(zip(self.__tests, self.__verdicts)):
			result: Dict[str, Any] = {}

			result["id"] = i
			result["name"] = test.name()
			result["categories"] = list(test.categories())
			result["passed"] = verdict.is_success()
			result["verdict"] = verdict.verdict_message()
			result["what"] = verdict.what() if verdict.is_failed() else ""

			runs: List[Dict[str, Any]] = []

			for r, _ in test.runs():
				run: Dict[str, Any] = {}

				run["timeout"] = r.get_timeout()
				run["stdin"] = escape(r.get_stdin()) if r.stdin_presented() else ""
				run["args"] = [escape(arg) for arg in r.get_args()] if r.args_presented() else ""
				run["expected_returncode"] = r.get_expected_returncode() if r.expected_returncode_presented() else ""
				run["expected_stdout"] = r.get_expected_stdout() if r.expected_stdout_presented() else ""
				run["stderr_should_be_empty"] = r.is_stderr_should_be_empty()

				runs.append(run)

			result["runs"] = runs

			results.append(result)

		return results

	def export_report(self, output_path: str, coefficients: Dict[str, float]):
		categories = coefficients.keys()

		j: Dict[str, Any] = {}

		j["result"] = self.__calculate_total(coefficients)
		j["categories"] = self.__get_results_by_categories(categories)
		j["tests"] = self.__get_results()

		o = json.dumps(j, indent = 4)

		with open(output_path, "w") as file:
			file.write(f"{o}\n")

class Tester:
	def __init__(self, testsuite_name: str):
		self.__tests: List[Test] = []
		self.__testsuite_name = testsuite_name
		self.__log = Log(indent_factor = 4)

	def add(self, test: Test):
		self.__tests.append(test)

	def warm(self, executable_path: str, timeout_factor: float):
		print(f"=== Warming `{self.__testsuite_name}`...")
		for test in self.__tests:
			test.warm(executable_path, timeout_factor)

	def run(self, executable_path: str, timeout_factor: float) -> Result:
		print(f"=== Testing `{self.__testsuite_name}`...")

		result = Result(self.__tests)
		start = now()

		for test in self.__tests:
			verdict = self.__log.scope(f"Test '{test.name()}' starts...", lambda : test.invoke(executable_path, timeout_factor, self.__log))
			result.add(verdict)

		end = now()

		print(f"{"=" * 30}")
		print(f"{result.passed()}/{result.n()} tests passed in {end - start}ms")

		return result

class Testsuite(ABC):
	def __init__(self, name: str, prefenvname: str, catenvnames: Dict[str, str]):
		self.__name = name
		self.__prefenvname = prefenvname
		self.__catenvnames = catenvnames

	def name(self) -> str:
		return self.__name

	def get_coefficients(self) -> Dict[str, float]:
		coefficients: Dict[str, float] = {}
		categories = list(self.__catenvnames.keys())

		for category in categories:
			key = f"{self.__prefenvname.upper()}_{self.__name.upper()}_{self.__catenvnames[category]}"
			value = os.getenv(key)

			if value is None:
				value = 0.0
			else:
				try:
					value = float(value)
				except TypeError as _:
					value = 0.0

			coefficients[category] = value

		return coefficients

	@abstractmethod
	def get_tester(self) -> Tester:
		raise NotImplementedError("Testsuite::get_tester is not implemented")
