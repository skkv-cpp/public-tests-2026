from .suite import Run, Runned, Verdict
from testsuites import *

class __Live1(Testsuite):
	__SUITE_NANE = "live1"
	__TIMEOUT = 1
	__CATEGORIES_TO_ENVNAMES = { "pos": "POS", "neg": "NEG" }
	__TESTDATA = os.path.join("testdata", __SUITE_NANE)

	def __init__(self):
		super().__init__(self.__SUITE_NANE, PREFIX_ENVIRONMENT_NAME, self.__CATEGORIES_TO_ENVNAMES)

	def get_tester(self) -> Tester:
		tester = Tester(self.name())

		class __Expected(Expected):
			def __init__(self, answer_filename: str):
				super().__init__()
				self.__answer_filename = answer_filename

			def test(self, run: Run, runned: Runned) -> Verdict:
				output = runned.get_stdout()

				if not output.endswith("\n"):
					return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"newline at stdout's end expected")

				output_lines = output.splitlines()
				answer_lines = open(self.__answer_filename, "r").readlines()

				no_lines = len(output_lines)
				na_lines = len(answer_lines)

				if no_lines != na_lines:
					return Verdict(VerdictErrno.ERROR_ASSERTION, f"expected {na_lines} lines, but program returned {no_lines} lines", "check argparse", True)

				for i in range(na_lines):
					try:
						o = int(output_lines[i])
						a = int(answer_lines[i].rstrip())

						if a != o:
							return Verdict(VerdictErrno.ERROR_ASSERTION, f"expected {a} as {i + 1}th number, but actual is {o}", "check sorting", True)
					except Exception as _:
						return Verdict(VerdictErrno.ERROR_TYPE_ERROR, f"can't convert \"{escape(output_lines[i])}\" to integer")

				return ok()

		def __make_path_to(parent: str, filename: Optional[str] = None) -> str:
			path = os.path.join(self.__TESTDATA, parent)

			if filename:
				path = os.path.join(path, filename)

			return path

		def __single_test(parent_basedir: str, timeout: int) -> SingleTest:
			args_test_filename = __make_path_to(parent_basedir, f"args.txt")
			answer_filename = __make_path_to(parent_basedir, f"answer.txt")
			args = open(args_test_filename, "r").readline().strip().split(" ")
			run = Run(c_timeout = timeout, c_stdin = None, c_args = args, c_cwd = __make_path_to(parent_basedir), t_returncode_policy = ReturnCodePolicy.ShouldBeZero)
			expected = __Expected(answer_filename)
			return (run, expected)

		def __single_args_test(args: List[str], cwd: Optional[str]) -> SingleTest:
			run = Run(c_timeout = self.__TIMEOUT, c_stdin = None, c_args = args, c_cwd = cwd, t_returncode_policy = ReturnCodePolicy.MatchIfPresented, t_returncode = 1, t_stderr_empty = False)
			return (run, None)

		def __sequence(parent: str, timeout: int) -> List[SingleTest]:
			return [__single_test(parent, timeout)]

		def __args_sequence(args: List[str], cwd: Optional[str]) -> List[SingleTest]:
			return [__single_args_test(args, cwd)]

		def __test(name: str, parent: str, timeout: int) -> Test:
			category = "pos"
			return Test(name, [category], __sequence(parent, timeout))

		def __args_test(name: str, args: List[str], cwd: Optional[str] = None) -> Test:
			category = "neg"
			return Test(name, [category], __args_sequence(args, cwd))

		def __t(i: int, parent: str, timeout: int):
			name = f"Livecoding test #{i} (see: ./testdata/{self.__SUITE_NANE}/{parent})"
			tester.add(__test(name, parent, timeout))

		def __a(name: str, args: str, cwd: Optional[str] = None):
			tester.add(__args_test(name, args.split(" "), cwd))

		def __make_test(i: int, timeout: int = self.__TIMEOUT):
			parent = f"test_{i}"
			__t(i, parent, timeout)

		for j in range(10):
			i = j + 1
			__make_test(i)	

		__make_test(11, 10) # 10 seconds for a lot of numbers

		__a("Less arguments #1", "$.txt 1")
		__a("Less arguments #2", "$.txt 1 1")

		__a("Too much arguments #1", "$.txt 1 1 2 hello")
		__a("Too much arguments #2", "$.txt 1 1 2 hello world this is me")

		__a("Bad arguments #1", "$.png -1 1 2")
		__a("Bad arguments #2", "$.png 1 -1 2")
		__a("Bad arguments #3", "$.png 1 1 -2")

		__a("No files", "$.png 1 1 2", __make_path_to("test_1"))

		return tester

instance = __Live1()
