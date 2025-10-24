#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import time
import termios
import tty

#######################################################
###### Configuration & Global Vars
#######################################################

config = {
  "log_dir": "/tmp/disk-diff",
  "dirs_to_check": ["/"],
  "file_categories": {
    "ignored": [
      "/var/lib/rsyslog/imjournal.state"
    ]
  },
  "dir_categories": {
    "ignored": [
      # These directories are ignored because they can cause permissions issues
      "/mnt",
      # These directories are ignored because they're very large, and typically irrelevant
      "/proc",            # ~611k
      "/sys",             # ~106k
      "/var/lib/docker",  # ~1.2m
      # These directories are ignored because they're cluttery
      "/root/.vscode-server",
      "/run/docker/runtime-runc",
      "/run/log/journal",
      # Lets just ignore everything in unimportant for now
      "/dev",
      "/run",
      "/usr/lib/.build-id",
      "/var/cache",
      "/var/run"
    ],
    "unimportant": [
      "/dev",
      "/run",
      "/usr/lib/.build-id",
      "/var/cache",
      "/var/run"
    ],
    "notable": [
      "/lib",
      "/tmp",
      "/usr/include",
      "/usr/lib",
      "/usr/share",
      "/usr/src"
    ],
    "key": [
      "/usr/local",
      "/var",
      "/root",
      "/home",
      "/opt",
      "/etc",
      "/bin",
      "/sbin",
      "/usr/bin",
      "/usr/sbin",
      "/usr/local/bin",
      "/usr/local/sbin",
      "/usr/lib/systemd/system",
    ]
  }
}

system = {
  "start_time": float,
  "end_time": float,
  "log_path": str,
  "get_files_first_call": True,
  "files_examined_count": int,
  "dirs_to_check": [],
  "uncategorized_files": {
    "born": [],
    "modified": [],
    "changed": [],
    "accessed": []
  },
  "categorized_files": {
    "logs": {
      "born": [],
      "modified": [],
      "changed": [],
      "accessed": []
    },
    "ignored": {
      "born": [],
      "modified": [],
      "changed": [],
      "accessed": []
    },
    "unimportant": {
      "born": [],
      "modified": [],
      "changed": [],
      "accessed": []
    },
    "notable": {
      "born": [],
      "modified": [],
      "changed": [],
      "accessed": []
    },
    "key": {
      "born": [],
      "modified": [],
      "changed": [],
      "accessed": []
    }
  }
}

#######################################################
###### Orchestration
#######################################################

def start():
  handle_args()
  handle_logs()
  set_dirs_to_check()

  manual_trigger = system["args"].command[0] == "man" or system["args"].command[0] == "manual"
  # This accounts for a strange bug where stat times can appear slightly before the start time
  system["start_time"] = time.time() - 0.02
  if manual_trigger:
    overwrite_last_line("Press enter when ready to scan...")
    wait_for_keypress()
  else:
    execute_subprocess()
  system["end_time"] = time.time()

  index_files()
  output_num_of_uncategorized_files()
  categorize_uncategorized_files()
  output_categorized_files()


def handle_logs():
  make_log_dir()
  set_log_path()


def categorize_uncategorized_files():
  set_ignored_files()
  set_key_files()
  set_log_files()
  set_notable_files()
  set_unimportant_files()


def set_log_files():
  set_born_log_files()
  set_modified_log_files()
  set_changed_log_files()
  set_accessed_log_files()


def set_ignored_files():
  set_born_ignored_files()
  set_modified_ignored_files()
  set_changed_ignored_files()
  set_accessed_ignored_files()


def set_unimportant_files():
  set_born_unimportant_files()
  set_modified_unimportant_files()
  set_changed_unimportant_files()
  set_accessed_unimportant_files()


def set_notable_files():
  set_born_notable_files()
  set_modified_notable_files()
  set_changed_notable_files()
  set_accessed_notable_files()


def set_key_files():
  set_born_key_files()
  set_modified_key_files()
  set_changed_key_files()
  set_accessed_key_files()


def index_files():
  overwrite_last_line("Indexing files...")
  dirs_to_check = system["dirs_to_check"]
  set_uncategorized_files(dirs_to_check)

#######################################################
###### Pre-Execution
#######################################################

def handle_args():
  parser = argparse.ArgumentParser(
    description="Show disk changes caused by an operation."
  )
  parser.add_argument(
    "command",
    type=str,
    nargs='+',
    help='Command to execute. Alternatively, keyword "manual"'
  )
  parser.add_argument(
    "-b", "--no-born",
    action="store_true",
    help="Toggles including files born during the operation.\nDefault On."
  )
  parser.add_argument(
    "-m", "--no-modified",
    action="store_true",
    help="Toggles including files modified during the operation.\nDefault On."
  )
  parser.add_argument(
    "-c", "--no-changed",
    action="store_true",
    help="Toggles including files changed during the operation.\nDefault Off."
  )
  parser.add_argument(
    "-a", "--no-accessed",
    action="store_true",
    help="Toggles including files accessed during the operation.\nDefault Off."
  )
  parser.add_argument(
    "-d", "--dir",
    action="append",
    type=argparse_is_dir,
    help="Adds a directory to check -- Overwrites dirs in config.\nDefault is what's in config."
  )
  parser.add_argument(
    "--dodge",
    action="append",
    type=str,
    help="Adds a keyword to dodge -- Will skip any file path with {value} in it."
  )
  args = parser.parse_args()
  system["args"] = args

#######################################################
###### Execution
#######################################################

def execute_subprocess():
  command = system["args"].command
  try:
    subprocess.run(command, check=True)
  except subprocess.CalledProcessError as e:
    red = "\033[38;5;160m"
    white = "\033[0m"
    print(f"\n{red}Subprocess failed with exit code:{white} {e.returncode}\n")

def make_log_dir():
  log_dir = config["log_dir"]
  os.makedirs(log_dir, exist_ok=True)

def wait_for_keypress():
  fd = sys.stdin.fileno()
  old = termios.tcgetattr(fd)
  try:
    tty.setraw(fd)
    sys.stdin.read(1)
  finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old)

#######################################################
###### Data Manipulation
#######################################################

def set_dirs_to_check():
  if system["args"].dir is not None:
    system["dirs_to_check"] = system["args"].dir
  else:
    system["dirs_to_check"] = config["dirs_to_check"]


def set_log_path():
  command_as_filename = get_command_as_filename()
  if command_as_filename:
    set_log_path_using_command(command_as_filename)
  else:
    set_log_path_using_time()


def set_log_path_using_command(command_as_filename):
  LOG_PATH = os.path.join(
    config["log_dir"],
    f"{command_as_filename}.log"
  )
  system["log_path"] = LOG_PATH


def set_log_path_using_time():
  current_time = time.time()
  log_path = os.path.join(
    config["log_dir"],
    f"manual-{current_time}.log"
  )
  system["log_path"] = log_path


def set_born_ignored_files():
  ignored_born_files = system["categorized_files"]["ignored"]["born"]
  ignored_dirs = config["dir_categories"]["ignored"]
  set_some_born_files(ignored_born_files, ignored_dirs)


def set_modified_ignored_files():
  ignored_modified_files = system["categorized_files"]["ignored"]["modified"]
  ignored_dirs = config["dir_categories"]["ignored"]
  set_some_modified_files(ignored_modified_files, ignored_dirs)


def set_changed_ignored_files():
  ignored_changed_files = system["categorized_files"]["ignored"]["changed"]
  ignored_dirs = config["dir_categories"]["ignored"]
  set_some_changed_files(ignored_changed_files, ignored_dirs)


def set_accessed_ignored_files():
  ignored_accessed_files = system["categorized_files"]["ignored"]["accessed"]
  ignored_dirs = config["dir_categories"]["ignored"]
  set_some_accessed_files(ignored_accessed_files, ignored_dirs)


def set_born_unimportant_files():
  unimportant_born_files = system["categorized_files"]["unimportant"]["born"]
  unimportant_dirs = config["dir_categories"]["unimportant"]
  set_some_born_files(unimportant_born_files, unimportant_dirs)


def set_modified_unimportant_files():
  unimportant_modified_files = system["categorized_files"]["unimportant"]["modified"]
  unimportant_dirs = config["dir_categories"]["unimportant"]
  set_some_modified_files(unimportant_modified_files, unimportant_dirs)


def set_changed_unimportant_files():
  unimportant_changed_files = system["categorized_files"]["unimportant"]["changed"]
  unimportant_dirs = config["dir_categories"]["unimportant"]
  set_some_changed_files(unimportant_changed_files, unimportant_dirs)


def set_accessed_unimportant_files():
  unimportant_accessed_files = system["categorized_files"]["unimportant"]["accessed"]
  unimportant_dirs = config["dir_categories"]["unimportant"]
  set_some_accessed_files(unimportant_accessed_files, unimportant_dirs)


def set_born_log_files():
  uncategorized_born_files = system["uncategorized_files"]["born"]
  born_logs = system["categorized_files"]["logs"]["born"]
  for file_path in uncategorized_born_files.copy():
    if is_log_file(file_path):
      born_logs.append(file_path)
      uncategorized_born_files.remove(file_path)


def set_modified_log_files():
  uncategorized_modified_files = system["uncategorized_files"]["modified"]
  modified_logs = system["categorized_files"]["logs"]["modified"]
  for file_path in uncategorized_modified_files.copy():
    if is_log_file(file_path):
      modified_logs.append(file_path)
      uncategorized_modified_files.remove(file_path)

def set_changed_log_files():
  uncategorized_changed_files = system["uncategorized_files"]["changed"]
  changed_logs = system["categorized_files"]["logs"]["changed"]
  for file_path in uncategorized_changed_files.copy():
    if is_log_file(file_path):
      changed_logs.append(file_path)
      uncategorized_changed_files.remove(file_path)

def set_accessed_log_files():
  uncategorized_accessed_files = system["uncategorized_files"]["accessed"]
  accessed_logs = system["categorized_files"]["logs"]["accessed"]
  for file_path in uncategorized_accessed_files.copy():
    if is_log_file(file_path):
      accessed_logs.append(file_path)
      uncategorized_accessed_files.remove(file_path)


def set_born_notable_files():
  notable_born_files = system["categorized_files"]["notable"]["born"]
  notable_dirs = config["dir_categories"]["notable"]
  set_some_born_files(notable_born_files, notable_dirs)


def set_modified_notable_files():
  notable_modified_files = system["categorized_files"]["notable"]["modified"]
  notable_dirs = config["dir_categories"]["notable"]
  set_some_modified_files(notable_modified_files, notable_dirs)


def set_changed_notable_files():
  notable_changed_files = system["categorized_files"]["notable"]["changed"]
  notable_dirs = config["dir_categories"]["notable"]
  set_some_changed_files(notable_changed_files, notable_dirs)


def set_accessed_notable_files():
  notable_accessed_files = system["categorized_files"]["notable"]["accessed"]
  notable_dirs = config["dir_categories"]["notable"]
  set_some_accessed_files(notable_accessed_files, notable_dirs)


def set_born_key_files():
  key_born_files = system["categorized_files"]["key"]["born"]
  key_dirs = config["dir_categories"]["key"]
  set_some_born_files(key_born_files, key_dirs)


def set_modified_key_files():
  key_modified_files = system["categorized_files"]["key"]["modified"]
  key_dirs = config["dir_categories"]["key"]
  set_some_modified_files(key_modified_files, key_dirs)


def set_changed_key_files():
  key_changed_files = system["categorized_files"]["key"]["changed"]
  key_dirs = config["dir_categories"]["key"]
  set_some_changed_files(key_changed_files, key_dirs)


def set_accessed_key_files():
  key_accessed_files = system["categorized_files"]["key"]["accessed"]
  key_dirs = config["dir_categories"]["key"]
  set_some_accessed_files(key_accessed_files, key_dirs)


def set_some_born_files(some_born_files, some_criteria_dirs):
  uncategorized_born_files = system["uncategorized_files"]["born"]
  set_some_files(uncategorized_born_files, some_born_files, some_criteria_dirs)


def set_some_modified_files(some_modified_files, some_criteria_dirs):
  uncategorized_modified_files = system["uncategorized_files"]["modified"]
  set_some_files(uncategorized_modified_files, some_modified_files, some_criteria_dirs)


def set_some_changed_files(some_changed_files, some_criteria_dirs):
  uncategorized_changed_files = system["uncategorized_files"]["changed"]
  set_some_files(uncategorized_changed_files, some_changed_files, some_criteria_dirs)


def set_some_accessed_files(some_accessed_files, some_criteria_dirs):
  uncategorized_accessed_files = system["uncategorized_files"]["accessed"]
  set_some_files(uncategorized_accessed_files, some_accessed_files, some_criteria_dirs)


def set_some_files(some_uncategorized_files, some_files, some_criteria_dirs):
  for directory in some_criteria_dirs:
    for file_path in some_uncategorized_files.copy():
      is_some_file = is_file_of_directory(file_path, directory)
      if is_some_file:
        some_files.append(file_path)
        some_uncategorized_files.remove(file_path)

#######################################################
###### Output
#######################################################

def output_num_of_uncategorized_files():
  file_count = len(get_all_uncategorized_files())
  files_to_categorize_formatted = f"{file_count:,}"
  overwrite_last_line(f"Categorized files: {files_to_categorize_formatted}\n")


def output_categorized_files():
  any_ignored_files = len(get_all_ignored_files()) > 0
  any_unimportant_files = len(get_all_unimportant_files()) > 0
  any_notable_files = len(get_all_notable_files()) > 0
  any_key_files = len(get_all_key_files()) > 0
  any_log_files = len(get_all_log_files()) > 0
  any_uncategorized_files = len(get_all_uncategorized_files()) > 0

  truncate_file(system["log_path"])   # TODO: Probably we shouldn't just truncate the file every time

  if any_ignored_files:
    output_ignored_files()
  if any_unimportant_files:
    output_unimportant_files()
  if any_notable_files:
    output_notable_files()
  if any_key_files:
    output_key_files()
  if any_log_files:
    output_log_files()
  if any_uncategorized_files:
    output_uncategorized_files()
  print()


def output_ignored_files():
  tag = "Ignored"
  grey = "\033[38;5;242m"
  ignored_categorized_files = system["categorized_files"]["ignored"]
  output_some_files(tag, ignored_categorized_files, grey)


def output_unimportant_files():
  tag = "Unimportant"
  red = "\033[38;5;160m"
  unimportant_categorized_files = system["categorized_files"]["unimportant"]
  output_some_files(tag, unimportant_categorized_files, red)


def output_notable_files():
  tag = "Notable"
  yellow = "\033[38;5;190m"
  notable_categorized_files = system["categorized_files"]["notable"]
  output_some_files(tag, notable_categorized_files, yellow)


def output_key_files():
  tag = "Key"
  green = "\033[38;5;46m"
  key_categorized_files = system["categorized_files"]["key"]
  output_some_files(tag, key_categorized_files, green)


def output_log_files():
  tag = "Logs"
  blue = "\033[38;5;39m"
  log_files = system["categorized_files"]["logs"]
  output_some_files(tag, log_files, blue)


def output_uncategorized_files():
  tag = "Uncategorized"
  white = "\033[0m"
  uncategorized_categorized_files = system["uncategorized_files"]
  output_some_files(tag, uncategorized_categorized_files, white)


def output_some_files(tag, some_categorized_files, color):
  print(f"\n{tag}:")
  append_to_file(system["log_path"], f"\n_____{tag}_____")
  output_some_born_files(some_categorized_files["born"], color)
  output_some_modified_files(some_categorized_files["modified"], color)
  output_some_changed_files(some_categorized_files["changed"], color)
  output_some_accessed_files(some_categorized_files["accessed"], color)


def output_some_born_files(some_categorized_born_files, color):
  white = "\033[0m"
  for file_path in some_categorized_born_files:
    print(f"      Born: {color}{file_path}{white}")
    append_to_file(system["log_path"], f"      Born: {file_path}")


def output_some_modified_files(some_categorized_modified_files, color):
  white = "\033[0m"
  for file_path in some_categorized_modified_files:
    print(f"  Modified: {color}{file_path}{white}")
    append_to_file(system["log_path"], f"  Modified: {file_path}")


def output_some_changed_files(some_categorized_changed_files, color):
  white = "\033[0m"
  for file_path in some_categorized_changed_files:
    print(f"   Changed: {color}{file_path}{white}")
    append_to_file(system["log_path"], f"   Changed: {file_path}")


def output_some_accessed_files(some_categorized_accessed_files, color):
  white = "\033[0m"
  for file_path in some_categorized_accessed_files:
    print(f"  Accessed: {color}{file_path}{white}")
    append_to_file(system["log_path"], f"  Accessed: {file_path}")

#######################################################
###### Low Level Helpers / Utilities
#######################################################

def get_command_as_filename():
  command = system["args"].command
  command_as_string = ' '.join(command)
  command_as_filename = command_as_string.lower().replace(" ", "_").replace("/", "_")

  return command_as_filename


def set_uncategorized_files(dirs):
  for directory in dirs:
    for file_name in os.listdir(directory):
      file_path = os.path.join(directory, file_name)
      if dodge_keyword_is_in_file_path(file_path):
        continue
      if os.path.islink(file_path):
        continue  # Ignore symlinks for now
      if os.path.isdir(file_path):
        if file_path not in config["dir_categories"]["ignored"]:
          set_uncategorized_files([file_path])
      if os.path.isfile(file_path):
        if is_valid_born_file(file_path):
          system["uncategorized_files"]["born"].append(file_path)
        elif is_valid_modified_file(file_path):
          system["uncategorized_files"]["modified"].append(file_path)
        elif is_valid_changed_file(file_path):
          system["uncategorized_files"]["changed"].append(file_path)
        elif is_valid_accessed_file(file_path):
          system["uncategorized_files"]["accessed"].append(file_path)


def dodge_keyword_is_in_file_path(file_path):
  if system["args"].dodge is not None:
    for keyword in system["args"].dodge:
      if keyword in file_path:
        return True
  return False


def get_all_ignored_files():
  return (
    system["categorized_files"]["ignored"]["born"]
    + system["categorized_files"]["ignored"]["modified"]
    + system["categorized_files"]["ignored"]["changed"]
    + system["categorized_files"]["ignored"]["accessed"]
  )


def get_all_unimportant_files():
  return (
    system["categorized_files"]["unimportant"]["born"]
    + system["categorized_files"]["unimportant"]["modified"]
    + system["categorized_files"]["unimportant"]["changed"]
    + system["categorized_files"]["unimportant"]["accessed"]
  )


def get_all_notable_files():
  return (
    system["categorized_files"]["notable"]["born"]
    + system["categorized_files"]["notable"]["modified"]
    + system["categorized_files"]["notable"]["changed"]
    + system["categorized_files"]["notable"]["accessed"]
  )


def get_all_key_files():
  return (
    system["categorized_files"]["key"]["born"]
    + system["categorized_files"]["key"]["modified"]
    + system["categorized_files"]["key"]["changed"]
    + system["categorized_files"]["key"]["accessed"]
  )


def get_all_log_files():
  return (
    system["categorized_files"]["logs"]["born"]
    + system["categorized_files"]["logs"]["modified"]
    + system["categorized_files"]["logs"]["changed"]
    + system["categorized_files"]["logs"]["accessed"]
  )


def get_all_uncategorized_files():
  return (
    system["uncategorized_files"]["born"]
    + system["uncategorized_files"]["modified"]
    + system["uncategorized_files"]["changed"]
    + system["uncategorized_files"]["accessed"]
  )

#######################################################
###### High Level Helpers / Utilities
#######################################################

def truncate_file(file_path):
  with open(file_path, "w", encoding="utf-8"):
    pass


def append_to_file(file_path, content):
  with open(file_path, "a", encoding="utf-8") as f:
    f.write(f"{content}\n")


def overwrite_last_line(content):
  print(f"\r\033[K\t{content}", end="", flush=True)


#######################################################
###### Validation
#######################################################

def argparse_is_dir(directory):
  if os.path.isdir(directory):
    return directory
  raise argparse.ArgumentTypeError(f"Not a valid directory: {directory}")


def is_subdirectory(potential_sub_dir, dir2):
  dir2_length = len(dir2)
  potential_sub_dir_root = potential_sub_dir[:dir2_length]

  return potential_sub_dir_root == dir2


def is_file_of_directory(file_path, directory):
  is_direct_file_of_dir = os.path.dirname(file_path) == directory
  is_indirect_file_of_dir = is_subdirectory(os.path.dirname(file_path), directory)
  if is_direct_file_of_dir or is_indirect_file_of_dir:
    return True
  return False


def is_log_file(file_path):
  directory = os.path.dirname(file_path)
  file_name = os.path.basename(file_path)
  return (
    "logs" in directory
    or (
      "log" in file_name
      and "login" not in file_name
    )
  )


def is_valid_born_file(file_path):
  start_time = system["start_time"]
  end_time = system["end_time"]
  birth_time = os.stat(file_path).st_ctime

  return (
    not system["args"].no_born
    and start_time < birth_time < end_time
  )


def is_valid_modified_file(file_path):
  start_time = system["start_time"]
  end_time = system["end_time"]
  modified_time = os.stat(file_path).st_mtime

  return (
    not system["args"].no_modified
    and end_time > modified_time > start_time
  )


def is_valid_changed_file(file_path):
  start_time = system["start_time"]
  end_time = system["end_time"]
  changed_time = os.stat(file_path).st_ctime
  return (
    not system["args"].no_changed
    and end_time > changed_time > start_time
  )


def is_valid_accessed_file(file_path):
  start_time = system["start_time"]
  end_time = system["end_time"]
  access_time = os.stat(file_path).st_atime

  return (
    not system["args"].no_accessed
    and end_time > access_time > start_time
  )

#######################################################
###### Entrypoint
#######################################################

start()
