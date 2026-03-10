from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass


TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class Version:
  major: int
  minor: int
  patch: int

  def bump(self, level: str) -> "Version":
    if level == "major":
      return Version(self.major + 1, 0, 0)
    if level == "minor":
      return Version(self.major, self.minor + 1, 0)
    if level == "patch":
      return Version(self.major, self.minor, self.patch + 1)
    raise ValueError(f"unknown bump level: {level}")

  def render(self) -> str:
    return f"v{self.major}.{self.minor}.{self.patch}"


def run_git(*args: str) -> str:
  return subprocess.check_output(
    ["git", *args],
    text=True,
    stderr=subprocess.DEVNULL,
  ).strip()


def parse_version(tag: str) -> Version | None:
  match = TAG_PATTERN.match(tag)
  if not match:
    return None
  return Version(*(int(part) for part in match.groups()))


def highest_version(tags: list[str]) -> Version:
  versions = [version for tag in tags if (version := parse_version(tag)) is not None]
  if not versions:
    return Version(0, 0, 0)
  return max(versions, key=lambda item: (item.major, item.minor, item.patch))


def get_last_tag() -> str | None:
  try:
    return run_git("describe", "--tags", "--abbrev=0", "--match", "v*")
  except subprocess.CalledProcessError:
    return None


def commits_since(ref: str | None) -> list[str]:
  range_spec = f"{ref}..HEAD" if ref else "HEAD"
  output = run_git("log", "--format=%B%x00", range_spec)
  return [entry.strip() for entry in output.split("\x00") if entry.strip()]


def determine_bump(commits: list[str]) -> str | None:
  bump = None
  for message in commits:
    header = message.splitlines()[0]
    if "BREAKING CHANGE:" in message or re.match(r"^[a-z]+(\([^)]+\))?!:", header):
      return "major"
    if header.startswith("feat:") or re.match(r"^feat\([^)]+\):", header):
      bump = "minor"
    elif bump is None and (header.startswith("fix:") or re.match(r"^fix\([^)]+\):", header)):
      bump = "patch"
  return bump


def head_has_tag() -> bool:
  tags = run_git("tag", "--points-at", "HEAD").splitlines()
  return any(TAG_PATTERN.match(tag) for tag in tags)


def main() -> int:
  if head_has_tag():
    print("skip")
    return 0

  last_tag = get_last_tag()
  commits = commits_since(last_tag)
  bump = determine_bump(commits)
  if bump is None:
    print("skip")
    return 0

  if last_tag:
    current = parse_version(last_tag)
    if current is None:
      tags = run_git("tag", "--list", "v*").splitlines()
      current = highest_version(tags)
  else:
    tags = run_git("tag", "--list", "v*").splitlines()
    current = highest_version(tags)

  print(current.bump(bump).render())
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
