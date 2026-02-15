from testsuites import *
from typing import List

class __Intro(Testsuite):
	__SUITE_NAME = "intro"
	__TIMEOUT = 1
	__CATEGORIES_TO_ENVNAMES = { "a + b": "A_PLUS_B" }

	def __init__(self):
		super().__init__(self.__SUITE_NAME, PREFIX_ENVIRONMENT_NAME, self.__CATEGORIES_TO_ENVNAMES)

	def get_tester(self) -> Tester:
		tester = Tester(self.name())

		class __Expected(Expected):
			def __init__(self, a: int, b: int):
				super().__init__()

				self.__a = a
				self.__b = b

			def test(self, run: Run, runned: Runned) -> Verdict:
				try:
					output = runned.get_stdout()
					if not output.endswith("\n"):
						return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"newline at stdout's end expected")
 
					lines = output.splitlines()
					if len(lines) != 1:
						return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"single line expected")

					line = lines[0]
					if line != line.lstrip() or line != line.rstrip():
						return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"found unexpected space characters in stdout")

					actual = int(line)
					expected = self.__a + self.__b

					if actual != expected:
						return Verdict(VerdictErrno.ERROR_ASSERTION, f"{self.__a} + {self.__b} = {expected}, (actual: {actual})", "check math", True)

					return ok()
				except Exception as _:
					return Verdict(VerdictErrno.ERROR_TYPE_ERROR, f"can't convert \"{escape(runned.get_stdout())}\" to integer")

		def __single_test(a: int, b: int) -> SingleTest:
			run = Run(c_timeout = self.__TIMEOUT, c_stdin = f"{a} {b}", c_args = None, t_returncode_policy = ReturnCodePolicy.ShouldBeZero)
			expected = __Expected(a, b)
			return (run, expected)

		def __sequence(a: int, b: int) -> List[SingleTest]:
			return [__single_test(a, b)]

		def __test(a: int, b: int) -> Test:
			name = f"{a} + {b}"
			test = Test(name = name, categories = ["a + b"], sequence = __sequence(a, b))
			return test

		def t(a: int, b: int):
			tester.add(__test(a, b))

		for a in range(-5, 10):
			for b in range(6, 9):
				t(a, b)

		return tester

instance = __Intro()
