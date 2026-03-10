from .suite import Run, Runned, Verdict
from testsuites import *

class __SparseMatrix(Testsuite):
	__SUITE_NAME = "sparse_matrix"
	__TIMEOUT = 1
	__CATEGORIES_TO_ENVNAMES = {"det": "DET", "add": "ADD", "mul": "MUL", "pow": "POW", "sub": "SUB", "neg": "NEG"}
	__TESTDATA = os.path.join("testdata", __SUITE_NAME)

	def __init__(self):
		super().__init__(self.__SUITE_NAME, PREFIX_ENVIRONMENT_NAME, self.__CATEGORIES_TO_ENVNAMES)

	def get_tester(self) -> Tester:
		epsilon = 1e-6
		no_solution = "no solution"

		tester = Tester(self.name())

		def parse_lines_to_matrix(lines: List[str]) -> Optional[Union[Verdict, Tuple[List[List[float]], int, int]]]:
			__HEADER_COORDINATE = f"%%MatrixMarket matrix coordinate real general"
			__HEADER_ARRAY = f"%%MatrixMarket matrix array real general"
			__COMMENT_PREFIX = f"%"

			if not lines[-1].endswith("\n"):
				return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"newline at eof expected")

			try:
				index = 0

				line = lines[index].removesuffix("\n")
				if line != line.lstrip() or line != line.rstrip():
					return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"found unexpected space characters in #{index + 1} line ('{escape(line.rstrip())}' vs. '{escape(line.lstrip())}')")

				if line != __HEADER_COORDINATE and line != __HEADER_ARRAY:
					if line == no_solution:
						return None
					return Verdict(VerdictErrno.ERROR_ASSERTION, f"first line must be format's magic header")

				is_array = line == __HEADER_ARRAY

				index += 1
				while lines[index].startswith(__COMMENT_PREFIX):
					index += 1

				line = 	lines[index].removesuffix("\n")
				if line != line.lstrip() or line != line.rstrip():
					return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"found unexpected space characters in #{index + 1} line")

				sizes_strs = line.split(" ")
				index += 1

				if is_array and len(sizes_strs) != 2:
					return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"in array format there is should be rows and columns in sizes")
				elif not is_array and len(sizes_strs) != 3:
					return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"in coordinate format there is should be rows, columns and entries in sizes")

				rows, columns = int(sizes_strs[0]), int(sizes_strs[1])
				matrix: List[List[float]] = [[0.0 for _ in range(columns)] for _ in range(rows)]

				if is_array:
					for column in range(columns):
						for row in range(rows):
							line = lines[index].removesuffix("\n")
							if line != line.lstrip() or line != line.rstrip():
								return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"found unexpected space characters in #{index + 1} line")
							matrix[row][column] = float(line)
				else:
					while index < len(lines):
						line = lines[index].removesuffix("\n")
						if line != line.lstrip() or line != line.rstrip():
							return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"found unexpected space characters in #{index + 1} line")
						elements = line.split(" ")
						if len(elements) != 3:
							return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"in coordinate format there is should be x, y and element for describing")
						row, column, elem = int(elements[0]), int(elements[1]), float(elements[2])
						matrix[row - 1][column - 1] = elem
						index += 1

				return matrix, rows, columns
			except IndexError as _:
				return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"matrix is not complete, can't be parsed")
			except ValueError as e:
				return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"found something very bad", str(e))

		class __Expected(Expected):
			def __init__(self, output_filename: str, expected_filename: str):
				super().__init__()

				self.__actual_path = output_filename
				self.__expected_path = expected_filename

			def test(self, run: Run, runned: Runned) -> Verdict:
				if runned.get_stdout() != "":
					return Verdict(VerdictErrno.ERROR_STDOUT_IS_NOT_EMPTY)

				expecteds = open(self.__expected_path, "r").readlines()
				actuals: List[str] = []

				try:
					actuals = open(self.__actual_path, "r").readlines()
				except FileNotFoundError as _:
					return Verdict(VerdictErrno.ERROR_FILE_NOT_FOUND, f"'{self.__actual_path}' is not created by user's program")

				expected = parse_lines_to_matrix(expecteds)
				assert not isinstance(expected, Verdict), f"Expected matrix is not valid: {expected.what()}"

				if expected:
					expected_mtx, expected_rows, expected_columns = expected

					actual = parse_lines_to_matrix(actuals)

					if isinstance(actual, Verdict):
						return actual

					if not actual:
						return Verdict(VerdictErrno.ERROR_ASSERTION, f"expected matrix, but found 'no solution'")

					actual_mtx, actual_rows, actual_columns = actual

					if expected_rows != actual_rows:
						return Verdict(VerdictErrno.ERROR_ASSERTION, f"expected {expected_rows} rows, but actual matrix's header: {actual_rows} rows")

					if expected_columns != actual_columns:
						return Verdict(VerdictErrno.ERROR_ASSERTION, f"expected {expected_columns} columns, but actual matrix's header: {expected_columns} columns")

					if len(actual_mtx) != actual_rows or any(len(actual_mtx_row) != actual_columns for actual_mtx_row in actual_mtx):
						return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"matrix's header info is not valid to actual matrix")

					rows = expected_rows
					columns = expected_columns

					for row in range(rows):
						actual_mtx_row = actual_mtx[row]
						expected_mtx_row = expected_mtx[row]
						for column in range(columns):
							actual_elem = actual_mtx_row[column]
							expected_elem = expected_mtx_row[column]
							if not abs(actual_elem - expected_elem) < epsilon:
								return Verdict(VerdictErrno.ERROR_ASSERTION, f"expected[{row}, {column}] != actual[{row, column}] (expected {expected_elem}, but found {actual_elem})")
				else:
					actual = parse_lines_to_matrix(actuals)

					if isinstance(actual, Verdict):
						return actual

					if actual:
						return Verdict(VerdictErrno.ERROR_ASSERTION, f"found matrix, when there is no solution")

				return ok()

		class __DetExpected(Expected):
			def __init__(self, output_filename: str, expected_filename: str):
				super().__init__()

				self.__output_filename = output_filename
				self.__expected_filename = expected_filename

			def test(self, run: Run, runned: Runned) -> Verdict:
				if runned.get_stdout() != "":
					return Verdict(VerdictErrno.ERROR_STDOUT_IS_NOT_EMPTY)

				if not os.path.exists(self.__output_filename):
					return Verdict(VerdictErrno.ERROR_FILE_NOT_FOUND, f"'{self.__output_filename}' is not created by user's program")

				outputs = open(self.__output_filename, "r").readlines()
				if len(outputs) != 1:
					return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"single line expected")

				output = outputs[0]

				if not output.endswith("\n"):
					return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"newline at eof expected")

				output = output.removesuffix("\n")

				if output != output.lstrip() or output != output.rstrip():
					return Verdict(VerdictErrno.ERROR_INVALID_FORMAT, f"found unexpected space characters in output")

				expected_str = open(self.__expected_filename, "r").readline().removesuffix("\n")

				if expected_str == no_solution and output != no_solution:
					return Verdict(VerdictErrno.ERROR_ASSERTION, f"expected no Det of matrix, but found value")

				if expected_str != no_solution and output == no_solution:
					return Verdict(VerdictErrno.ERROR_ASSERTION, f"expected Det of matrix, but found it's like no solution")

				if expected_str == no_solution and output == no_solution:
					return ok()

				try:
					actual = float(output)
					expected = float(expected_str)

					if not abs(actual - expected) < epsilon:
						return Verdict(VerdictErrno.ERROR_ASSERTION, f"Det(matrix) expected {expected}, but found {actual}")

				except Exception as _:
					return Verdict(VerdictErrno.ERROR_TYPE_ERROR, f"can't convert \"{escape(output)}\" to integer")

				return ok()

		def __make_path_to(parent: str, filename: str) -> str:
			return os.path.join(self.__TESTDATA, parent, filename)

		def __single_test(operation: str, parent: str) -> SingleTest:
			input1_filename = __make_path_to(parent, f"input1.mtx")
			input2_filename = __make_path_to(parent, f"input2.mtx")
			output_filename = __make_path_to(parent, f"output.mtx.user")
			expected_filename = __make_path_to(parent, f"output.mtx")
			run = Run(c_timeout = self.__TIMEOUT, c_stdin = None, c_args = [operation, output_filename, input1_filename, input2_filename], t_returncode_policy = ReturnCodePolicy.ShouldBeZero)
			expected = __Expected(output_filename, expected_filename)
			return (run, expected)

		def __single_det_test(parent: str) -> SingleTest:
			input1_filename = __make_path_to(parent, f"input1.mtx")
			output_filename = __make_path_to(parent, f"output.mtx.user")
			expected_filename = __make_path_to(parent, f"output.mtx")
			run = Run(c_timeout = self.__TIMEOUT, c_stdin = None, c_args = ["|", output_filename, input1_filename], t_returncode_policy = ReturnCodePolicy.ShouldBeZero)
			expected = __DetExpected(output_filename, expected_filename)
			return (run, expected)

		def __single_fail(args: List[str]) -> SingleTest:
			run = Run(c_timeout = self.__TIMEOUT, c_stdin = None, c_args = args, t_returncode_policy = ReturnCodePolicy.MatchIfPresented, t_returncode = 1, t_stderr_empty = False)
			return (run, None)

		def __sequence(operation: str, parent: str) -> List[SingleTest]:
			return [__single_test(operation, parent)]

		def __sequence_det(parent: str) -> List[SingleTest]:
			return [__single_det_test(parent)]

		def __sequence_fail(args: List[str]) -> List[SingleTest]:
			return [__single_fail(args)]

		def __test(operation: str, parent: str, category: str, name: str) -> Test:
			return Test(name, [category], __sequence(operation, parent))

		def __test_det(parent: str, category: str, name: str) -> Test:
			return Test(name, [category], __sequence_det(parent))

		def __test_fail(args: List[str], category: str, name: str) -> Test:
			return Test(name, [category], __sequence_fail(args))

		def __t(operation: str, parent: str, category: str, category_fullname: str, i: int):
			name = f"{category_fullname} #{i}"
			tester.add(__test(operation, parent, category, name))

		def __d(j: int):
			__CATEGORY = "det"

			i = j + 1
			category = __CATEGORY
			parent = f"test_{category}_{i}"
			name = f"Det(matrix) #{i}"

			tester.add(__test_det(parent, category, name))

		def __f(args: List[str], name: str):
			__CATEGORY = "neg"
			tester.add(__test_fail(args, __CATEGORY, name))

		testdatas: List[Tuple[str, str, str, int]] = [
			("add", "+", "matrix + matrix", 6),
			("mul", "*", "matrix multiplication", 8),
			("pow", "^", "pow(matrix, n)", 7),
			("sub", "-", "matrix - matrix", 6)
		]

		for testdata in testdatas:
			category, operation, category_fullname, n = testdata
			for j in range(n):
				i = j + 1
				parent = f"test_{category}_{i}"
				__t(operation, parent, category, category_fullname, i)

		__DET_N = 6
		for j in range(__DET_N):
			__d(j)

		__f([], "no args")
		__f(["+"], "only 1 argument")
		__f(["+", "output.txt", "file_not_found.txt"], "no input1 file")
		__f(["+", "output.txt", "file_not_found.txt", "file_not_found2.txt"], "no input 1 and input 2 file")

		return tester

instance = __SparseMatrix()
