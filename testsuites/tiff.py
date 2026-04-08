from .suite import Tester

from .suite import Run, Runned, Verdict
from testsuites import *

class __TIFF(Testsuite):
	__SUITE_NAME = "tiff"
	__TIMEOUT = 1
	__CATEGORIES_TO_ENVNAMES = { "rgb": "RGB", "gray": "GRAY", "neg": "NEG" }
	__TESTDATA = os.path.join("testdata", __SUITE_NAME)

	def __init__(self):
		super().__init__(self.__SUITE_NAME, PREFIX_ENVIRONMENT_NAME, self.__CATEGORIES_TO_ENVNAMES)

	def get_tester(self) -> Tester:
		tester = Tester(self.name())

		class __Expected(Expected):
			__OFFSET_TO_SHOW = 16

			def __init__(self, output_filename: str, reference_filename: str):
				super().__init__()

				self.__output_filename = output_filename
				self.__reference_filename = reference_filename

			def test(self, run: Run, runned: Runned) -> Verdict:
				if runned.get_stdout() != "":
					return Verdict(VerdictErrno.ERROR_STDOUT_IS_NOT_EMPTY, f"below is what was in the stdout", runned.get_stdout())

				if not os.path.exists(self.__output_filename):
					return Verdict(VerdictErrno.ERROR_FILE_NOT_FOUND, f"'{self.__output_filename}' is not created by user's program")

				output = open(self.__output_filename, "rb").read()
				reference = open(self.__reference_filename, "rb").read()

				n_output = len(output)
				n_reference = len(reference)
				n = min(n_reference, n_output)

				verdict_errno = VerdictErrno.ERROR_SUCCESS
				what: Optional[str] = None
				what_extended: List[str] = []
				fail = False

				for i in range(n):
					if output[i] == reference[i]:
						continue

					verdict_errno = VerdictErrno.ERROR_ASSERTION

					what = "wrong converting result"

					what_extended.append(f"Comparing '{self.__output_filename}' and '{self.__reference_filename}'...")
					if i != 0:
						what_extended.append(f". . . <truncated {i} same bytes> . . .")

					k = min(i + self.__OFFSET_TO_SHOW, n)
					for j in range(i, k):
						what_extended.append("%08X: %02X %02X" % (j, output[j], reference[j]))

					if (k - i) == self.__OFFSET_TO_SHOW:
						what_extended.append(f". . . <truncated output> . . .")

					fail = True

					break

				is_reference_bigger = n_reference > n_output
				if n_output != n_reference:
					if not fail:
						verdict_errno = VerdictErrno.ERROR_ASSERTION
						what = "wrong file size"
					if is_reference_bigger:
						what_extended.append(f"Reference file '{self.__reference_filename}' is bigger, than actual file '{self.__output_filename}'.")
					else:
						what_extended.append(f"Actual file '{self.__output_filename}' is bigger, than reference file '{self.__reference_filename}'.")

				return Verdict(verdict_errno, what, what_extended)

		def __make_path_to(filename: str) -> str:
			return os.path.abspath(os.path.join(self.__TESTDATA, filename))

		def __single_test(input_basename: str, reference_basename: Optional[str], returncode: int = ERROR_SUCCESS, output_filename_override: Optional[str] = None) -> SingleTest:
			input_filename = __make_path_to(input_basename)
			output_filename = __make_path_to(f"output.user") if output_filename_override is None else output_filename_override
			reference_filename = "" if reference_basename is None else __make_path_to(reference_basename)
			neg = returncode != ERROR_SUCCESS
			returncode_policy = ReturnCodePolicy.ShouldBeZero if not neg else ReturnCodePolicy.MatchIfPresented
			stderr_empty = not neg
			run = Run(c_timeout = self.__TIMEOUT, c_stdin = None, c_args = [input_filename, output_filename], t_returncode_policy = returncode_policy, t_returncode = returncode, t_stderr_empty = stderr_empty)
			expected = None
			if not neg:
				expected = __Expected(output_filename, reference_filename)
			return run, expected

		def __args_single_test(args: List[str]) -> SingleTest:
			run = Run(c_timeout = self.__TIMEOUT, c_stdin = None, c_args = args, t_returncode_policy = ReturnCodePolicy.MatchIfPresented, t_returncode = ERROR_ARGUMENTS_INVALID, t_stderr_empty = False)
			return run, None

		def __neg_single_test(input_basename: str, returncode: int, output_filename_override: Optional[str]) -> SingleTest:
			return __single_test(input_basename, None, returncode, output_filename_override)

		def __sequence(input_basename: str, reference_basename: str) -> List[SingleTest]:
			return [__single_test(input_basename, reference_basename)]

		def __neg_sequence(input_basename: str, returncode: int, output_filename_override: Optional[str]) -> List[SingleTest]:
			return [__neg_single_test(input_basename, returncode, output_filename_override)]

		def __arg_sequence(args: List[str]) -> List[SingleTest]:
			return [__args_single_test(args)]

		def __test(name: str, category: str, input_basename: str, reference_basename: str) -> Test:
			return Test(name, [category], __sequence(input_basename, reference_basename))

		def __neg_test(name: str, input_basename: str, returncode: int, output_filename_override: Optional[str]) -> Test:
			category = "neg"
			return Test(name, [category], __neg_sequence(input_basename, returncode, output_filename_override))

		def __arg_test(name: str, args: List[str]) -> Test:
			category = "neg"
			return Test(name, [category], __arg_sequence(args))

		category_counter: Dict[str, int] = dict((k, 0) for k in self.__CATEGORIES_TO_ENVNAMES.keys())

		def __testname(category: str, prefix: str, input_basename: str):
			category_counter[category] += 1

			test_basename = input_basename.removesuffix(".tiff")
			test_basename = test_basename.removesuffix(".pnm")
			test_basename = test_basename.removeprefix(prefix)
			test_basename = test_basename.removeprefix("_")

			name_prefix = f"Picture [format = {category}] #{category_counter[category]}"
			name_suffix = f"" if test_basename == "" else f": {" ".join(test_basename.split("_")).capitalize()}"

			return f"{name_prefix}{name_suffix}"

		def t1(category: str, prefix: str, input_basename: str, reference_basename: str):
			tester.add(__test(__testname(category, prefix, input_basename), category, input_basename, reference_basename))

		def t(category: str, prefix: str, exception_basename: Set[str] = set(), exception_prefixes: Set[str] = set()):
			reference_basename = f"{prefix}.{"pnm" if category == "rgb" else "pgm"}"

			for input_basename in os.listdir(self.__TESTDATA):
				if not input_basename.startswith(prefix) or any(input_basename.startswith(p) for p in exception_prefixes):
					continue

				if input_basename == reference_basename or input_basename in exception_basename:
					continue

				t1(category, prefix, input_basename, reference_basename)

		def n(name: str, input_basename: str, returncode: int, output_filename_override: Optional[str] = None):
			tester.add(__neg_test(name, input_basename, returncode, output_filename_override))

		def na(name: str, args: List[str]):
			tester.add(__arg_test(name, args))

		t("rgb", "const", exception_prefixes = {"constg"})
		t("gray", "constg")

		n("No input file found", "this_file_does_not_exists.tiff", ERROR_CANNOT_OPEN_FILE)
		n("Can't create output file", "const_tiff.pnm", ERROR_CANNOT_OPEN_FILE, os.path.abspath(os.path.join(self.__TESTDATA, "this_directory_does_not_exists", "output.pnm")))

		na("No args", [])
		na("1 arg provided", ["argument 1"])
		na("Too much arguments provided", ["argument 1", "argument 2", "argument 3"])

		return tester

instance = __TIFF()
