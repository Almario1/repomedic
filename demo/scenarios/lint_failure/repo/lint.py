"""Tiny repo-local style gate: no trailing whitespace, lines <= 79 chars."""

import sys

MAX_LINE = 79


def lint_file(path):
    problems = []
    with open(path, encoding="utf-8") as fh:
        for num, line in enumerate(fh.read().splitlines(), start=1):
            if line != line.rstrip():
                problems.append(f"{path}:{num}: trailing whitespace")
            if len(line) > MAX_LINE:
                problems.append(f"{path}:{num}: line too long ({len(line)} > {MAX_LINE})")
    return problems


def main(paths):
    problems = [p for path in paths for p in lint_file(path)]
    for p in problems:
        print(p)
    if problems:
        print("LINT FAILED")
        return 1
    print("lint ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
