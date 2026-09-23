"""The method × attribute matrix of guide §10, on a class small enough to check by hand."""

from class_cohesion import Readings, matrices_in, report

# Three obvious blocks — (read_a, write_a) on _a, read_b on _b, move on _x/_y — plus
# _log, the plumbing everybody touches, one dispatch method and one `async def`.
SAMPLE = '''
class Sample:
    def __init__(self, log, a, b):
        self._log = log
        self._a = a
        self._b = b
        self._solo: int = 1
        self._x, self._y = 0, 0

    def read_a(self):
        self._log.info(self._a)

    async def write_a(self):
        self._a = 1
        self._log.info("written")

    def read_b(self):
        return self._b + self._log.count

    def only_solo(self):
        return self._solo

    def dispatch(self):
        return self.read_a()

    def move(self):
        self._x, self._y = self._y, self._x
'''

PLUMBING = frozenset({"_log"})


def sample_readings() -> Readings:
    return matrices_in(SAMPLE, "Sample")[0].readings(PLUMBING)


def test_given_a_class_with_three_blocks_and_plumbing_when_measured_then_the_readings_show_them() -> None:
    assert sample_readings() == Readings(
        class_name="Sample",
        attributes=("_log", "_a", "_b", "_solo", "_x", "_y"),
        methods=("read_a", "write_a", "read_b", "only_solo", "dispatch", "move"),
        pairs=15,
        sharing_pairs=3,
        disjoint_pairs=12,
        tcc=0.2,
        sole_touched=(("_b", "read_b"), ("_solo", "only_solo"), ("_x", "move"), ("_y", "move")),
        empty_rows=("dispatch",),
        components=(("read_a", "read_b", "write_a"), ("only_solo",), ("dispatch",), ("move",)),
        components_without_plumbing=(
            ("read_a", "write_a"),
            ("read_b",),
            ("only_solo",),
            ("dispatch",),
            ("move",),
        ),
        touch_counts=(("_log", 3), ("_a", 2), ("_b", 1), ("_solo", 1), ("_x", 1), ("_y", 1)),
    )


def test_given_an_async_method_when_building_the_matrix_then_it_is_a_row_like_any_other() -> None:
    matrix = matrices_in(SAMPLE, "Sample")[0]

    assert [row.name for row in matrix.rows if row.touched == frozenset({"_a", "_log"})] == [
        "read_a",
        "write_a",
    ]


def test_given_a_file_of_several_classes_when_no_class_is_named_then_only_the_multi_method_ones() -> None:
    source = SAMPLE + "\n\nclass Lonely:\n    def one(self):\n        return 1\n"

    assert [m.class_name for m in matrices_in(source, None)] == ["Sample"]


def test_given_a_two_by_two_class_when_reporting_then_the_grid_marks_each_touch() -> None:
    source = "class Pair:\n    def __init__(self):\n        self._a = 1\n        self._b = 2\n"
    source += "\n    def m(self):\n        return self._a\n\n    def n(self):\n        return self._b\n"
    matrix = matrices_in(source, "Pair")[0]

    assert matrix.grid().splitlines()[:3] == [
        "   1  2  ",
        "m  ●  ·  ",
        "n  ·  ●  ",
    ]


def test_given_plumbing_is_named_when_reporting_then_both_component_counts_are_printed() -> None:
    matrix = matrices_in(SAMPLE, "Sample")[0]

    text = report(matrix, sample_readings(), PLUMBING)

    assert "attribute-only components: 4" in text
    assert "components without plumbing ['_log']: 5" in text
