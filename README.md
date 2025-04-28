# Disk Monitor

**Disk Monitor** is a lightweight utility that tracks filesystem changes before, during, and after executing a command — or manually triggered by user input. It identifies and categorizes file and directory activity to help monitor system behavior.

## Features

- Monitors file creations, modifications, metadata changes, and access during operations.
- Categorizes files and directories into key, notable, unimportant, ignored, and log categories.
- Provides color-coded console output for easy viewing.
- Saves detailed logs to a configurable directory.
- Supports manual operation mode or automatic execution of subprocesses.
- Customizable behavior via command-line flags.

## Installation

```bash
git clone git@github.com:coreyMerritt/disk-diff.git
cd disk-diff
chmod +x disk-diff
```

## Usage

Basic command structure:

```bash
sudo ./disk-diff -- [COMMAND]
```

Example to monitor a command:

```bash
sudo ./disk-diff -- sudo dnf update
```

Manual mode (user decides when to scan):

```bash
sudo ./disk-diff manual
```

### Available Flags

- `-b`, `--no-born`: Exclude newly created files from output.
- `-m`, `--no-modified`: Exclude modified files from output.
- `-c`, `--no-changed`: Exclude metadata-changed files from output.
- `-a`, `--no-accessed`: Exclude accessed files from output.

You can combine these flags as needed.

## Configuration

Default configurations are located at the beginning of the code, including:

- Directories to monitor.
- File and directory categories.
- Logging directory.

Feel free to modify the `config` dictionary in the script to adapt to your needs.

## License

This project is open-source and distributed under the [MIT License](LICENSE).

---

*Disclaimer: This tool makes filesystem observations and may miss rapid or very subtle file system changes in edge cases. Always test carefully for critical tasks.*

