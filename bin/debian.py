import os
import getpass
import socket
import ctypes
from pathlib import Path
import shutil
import sys
import select
import subprocess
from datetime import datetime
import textwrap
import platform
import time as time_module
import psutil

kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

class TerminalColors:
    GREEN = "\033[0;32m"
    CYAN = "\033[0;36m"
    RED = "\033[0;31m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    WHITE = "\033[1;37m"
    RESET = "\033[0m"

def get_prompt():
    username = getpass.getuser().lower()
    hostname = socket.gethostname().lower()
    current_dir = os.getcwd()
    home_dir = os.path.expanduser("~")
    
    if current_dir.startswith(home_dir):
        current_dir = "~" + current_dir[len(home_dir):]
    
    return f"{TerminalColors.GREEN}{username}@{hostname}{TerminalColors.RESET}:{TerminalColors.CYAN}{current_dir}{TerminalColors.RESET}$ "

def print_error(msg):
    print(f"{TerminalColors.RED}-bash: {msg}{TerminalColors.RESET}")

def handle_clear():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def handle_cowsay(text):
    if not text:
        text = ["Hello World"]
    else:
        text = " ".join(text)
        text = textwrap.wrap(text, width=40)

    max_len = max(len(line) for line in text) if isinstance(text, list) else len(text)
    
    print(" " + "_" * (max_len + 2))
    
    if isinstance(text, list):
        if len(text) == 1:
            print(f"< {text[0]} >")
        else:
            print(f"/ {text[0].ljust(max_len)} \\")
            for line in text[1:-1]:
                print(f"| {line.ljust(max_len)} |")
            print(f"\\ {text[-1].ljust(max_len)} /")
    else:
        print(f"< {text} >")
    
    print(" " + "-" * (max_len + 2))
    
    print("""
           \\   ^__^
            \\  (oo)\\_______
               (__)\\       )\\/\\
                   ||----w |
                   ||     ||
    """)

def handle_ls():
    try:
        items = os.listdir()
        print(' '.join(sorted(items)))
    except Exception as e:
        print_error(f"ls: {str(e).lower()}")

def handle_cd(path):
    try:
        if not path:
            return
        
        if path == "~":
            path = os.path.expanduser("~")
        elif path.startswith("~/"):
            path = os.path.join(os.path.expanduser("~"), path[2:])
        
        os.chdir(path)
    except FileNotFoundError:
        print_error(f"cd: {path}: No such file or directory")
    except Exception as e:
        print_error(f"cd: {str(e).lower()}")

def handle_pwd():
    try:
        print(os.getcwd())
    except Exception as e:
        print_error(f"pwd: {str(e).lower()}")

def handle_mkdir(paths):
    if not paths:
        print_error("mkdir: missing operand")
        return
    
    for path in paths:
        try:
            os.makedirs(path, exist_ok=True)
        except FileExistsError:
            print_error(f"mkdir: cannot create directory '{path}': File exists")
        except Exception as e:
            print_error(f"mkdir: cannot create directory '{path}': {str(e).lower()}")

def handle_rmdir(paths):
    if not paths:
        print_error("rmdir: missing operand")
        return
    
    for path in paths:
        try:
            os.rmdir(path)
        except FileNotFoundError:
            print_error(f"rmdir: failed to remove '{path}': No such file or directory")
        except OSError as e:
            if "Directory not empty" in str(e):
                print_error(f"rmdir: failed to remove '{path}': Directory not empty")
            else:
                print_error(f"rmdir: failed to remove '{path}': {str(e).lower()}")
        except Exception as e:
            print_error(f"rmdir: failed to remove '{path}': {str(e).lower()}")

def handle_cat(files):
    if not files:
        try:
            while True:
                line = input()
                print(line)
        except (KeyboardInterrupt, EOFError):
            return
    
    for file in files:
        try:
            with open(file, 'r') as f:
                content = f.read()
                print(content, end='')
                if not content.endswith('\n'):
                    print()
        except FileNotFoundError:
            print_error(f"cat: {file}: No such file or directory")
        except IsADirectoryError:
            print_error(f"cat: {file}: Is a directory")
        except Exception as e:
            print_error(f"cat: {file}: {str(e).lower()}")

def handle_touch(files):
    if not files:
        print_error("touch: missing file operand")
        return
    
    for file in files:
        try:
            Path(file).touch(exist_ok=True)
        except FileNotFoundError:
            print_error(f"touch: cannot touch '{file}': No such file or directory")
        except PermissionError:
            print_error(f"touch: cannot touch '{file}': Permission denied")
        except Exception as e:
            print_error(f"touch: cannot touch '{file}': {str(e).lower()}")

def handle_rm(args):
    if not args:
        print_error("rm: missing operand")
        print("Try 'rm --help' for more information.")
        return
    
    recursive = False
    force = False
    files = []
    
    for arg in args:
        if arg.startswith('-'):
            if 'r' in arg or 'R' in arg:
                recursive = True
            if 'f' in arg:
                force = True
        else:
            files.append(arg)
    
    if not files:
        print_error("rm: missing operand")
        return
    
    for file in files:
        try:
            if os.path.isdir(file):
                if recursive:
                    shutil.rmtree(file)
                else:
                    print(f"rm: cannot remove '{file}': Is a directory")
            else:
                os.remove(file)
        except FileNotFoundError:
            if not force:
                print_error(f"rm: cannot remove '{file}': No such file or directory")
        except Exception as e:
            if not force:
                print_error(f"rm: cannot remove '{file}': {str(e)}")

def handle_cp(args):
    if len(args) < 2:
        print_error("cp: missing file operand")
        print("Try 'cp --help' for more information.")
        return
    
    recursive = False
    force = False
    sources = []
    destination = None
    
    for arg in args:
        if arg.startswith('-'):
            if 'r' in arg or 'R' in arg:
                recursive = True
            if 'f' in arg:
                force = True
        elif destination is None:
            sources.append(arg)
        else:
            sources.append(destination)
            destination = arg

    if len(sources) > 0 and destination is None:
        destination = sources.pop()
    
    if not sources or destination is None:
        print_error("cp: missing file operand")
        return
    
    try:
        if len(sources) > 1 and not os.path.isdir(destination):
            print(f"cp: target '{destination}' is not a directory")
            return
        
        for src in sources:
            try:
                if os.path.isdir(src):
                    if recursive:
                        if os.path.isdir(destination):
                            dest_path = os.path.join(destination, os.path.basename(src))
                        else:
                            dest_path = destination
                        shutil.copytree(src, dest_path)
                    else:
                        print(f"cp: -r not specified; omitting directory '{src}'")
                else:
                    if os.path.isdir(destination):
                        dest_path = os.path.join(destination, os.path.basename(src))
                    else:
                        dest_path = destination
                    
                    if os.path.exists(dest_path) and not force:
                        print(f"cp: overwrite '{dest_path}'? (y/n) ", end='')
                        response = input().lower()
                        if response != 'y':
                            continue
                    
                    shutil.copy2(src, dest_path)
            except FileNotFoundError:
                print(f"cp: cannot stat '{src}': No such file or directory")
            except Exception as e:
                print(f"cp: cannot copy '{src}': {str(e)}")
    except Exception as e:
        print(f"cp: {str(e)}")

def handle_mv(args):
    if len(args) < 2:
        print_error("mv: missing file operand")
        print("Try 'mv --help' for more information.")
        return

    force = False
    sources = []
    destination = None

    for arg in args:
        if arg.startswith('-'):
            if 'f' in arg:
                force = True
        elif destination is None:
            sources.append(arg)
        else:
            sources.append(destination)
            destination = arg

    if len(sources) > 0 and destination is None:
        destination = sources.pop()

    if not sources or destination is None:
        print_error("mv: missing destination file operand")
        return

    if len(sources) > 1 and not os.path.isdir(destination):
        print(f"mv: target '{destination}' is not a directory")
        return

    for src in sources:
        try:
            if os.path.isdir(destination):
                dest_path = os.path.join(destination, os.path.basename(src))
            else:
                dest_path = destination

            if os.path.exists(dest_path) and not force:
                print(f"mv: overwrite '{dest_path}'? (y/n) ", end='')
                response = input().lower()
                if response != 'y':
                    continue

            shutil.move(src, dest_path)
        except FileNotFoundError:
            print(f"mv: cannot stat '{src}': No such file or directory")
        except Exception as e:
            print(f"mv: failed to move '{src}': {str(e)}")

def handle_less(files):
    if not files:
        print_error("less: missing file operand")
        return

    for file in files:
        try:
            encodings = ['utf-8', 'cp1251', 'cp1252', 'iso-8859-1', 'koi8-r']
            for encoding in encodings:
                try:
                    with open(file, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                        current_line = 0
                        total_lines = len(lines)
                        page_size = min(20, total_lines)

                        while current_line < total_lines:
                            for i in range(current_line, min(current_line + page_size, total_lines)):
                                print(lines[i], end='')
                            current_line += page_size

                            if current_line >= total_lines:
                                break

                            print("--More--", end='', flush=True)
                            try:
                                if sys.platform == 'win32':
                                    import msvcrt
                                    if msvcrt.kbhit():
                                        key = msvcrt.getch().decode('utf-8').lower()
                                        if key == 'q':
                                            print()
                                            return
                                        elif key == '/':
                                            print("\nSearch: ", end='')
                                            search_term = input().lower()
                                            for i, line in enumerate(lines[current_line:]):
                                                if search_term in line.lower():
                                                    current_line += i
                                                    break
                                else:
                                    if select.select([sys.stdin], [], [], 0)[0]:
                                        user_input = sys.stdin.readline().strip().lower()
                                        if user_input == 'q':
                                            print()
                                            return
                                        elif user_input.startswith('/'):
                                            search_term = user_input[1:]
                                            for i, line in enumerate(lines[current_line:]):
                                                if search_term in line.lower():
                                                    current_line += i
                                                    break
                            except KeyboardInterrupt:
                                print()
                                return
                    print()
                    break
                except UnicodeDecodeError:
                    continue
            
            else:
                print(f"less: cannot display '{file}': unsupported encoding")

        except FileNotFoundError:
            print_error(f"less: cannot open '{file}': No such file or directory")
        except IsADirectoryError:
            print_error(f"less: '{file}': Is a directory")
        except Exception as e:
            print_error(f"less: {str(e)}")

def handle_tree(path=".", level=0, max_depth=3):
    if level > max_depth:
        return

    prefix = "│   " * (level - 1) + "├── " if level > 0 else ""
    
    try:
        with os.scandir(path) as entries:
            entries = sorted(entries, key=lambda e: e.name)
            for entry in entries:
                if entry.is_dir():
                    print(f"{prefix}{TerminalColors.BLUE}{entry.name}{TerminalColors.RESET}")
                    handle_tree(entry.path, level + 1, max_depth)
                else:
                    print(f"{prefix}{TerminalColors.GREEN}{entry.name}{TerminalColors.RESET}")
    except PermissionError:
        print(f"{prefix}{TerminalColors.RED}[Permission denied]{TerminalColors.RESET}")
    except Exception as e:
        print_error(f"tree: {str(e)}")

def handle_head(args):
    if not args:
        print_error("head: missing file operand")
        return

    lines = 10
    files = []
    
    i = 0
    while i < len(args):
        if args[i] == '-n' and i + 1 < len(args):
            try:
                lines = int(args[i+1])
                i += 2
            except ValueError:
                print_error("head: invalid number of lines")
                return
        elif args[i].startswith('-'):
            print_error(f"head: invalid option -- '{args[i][1:]}'")
            return
        else:
            files.append(args[i])
            i += 1

    for file in files:
        try:
            with open(file, 'r') as f:
                print(f"==> {file} <==")
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    print(line, end='')
                print()
        except FileNotFoundError:
            print_error(f"head: cannot open '{file}' for reading: No such file or directory")
        except IsADirectoryError:
            print_error(f"head: error reading '{file}': Is a directory")
        except Exception as e:
            print_error(f"head: {str(e)}")

def handle_tail(args):
    if not args:
        print_error("tail: missing file operand")
        return

    lines = 10
    files = []
    
    i = 0
    while i < len(args):
        if args[i] == '-n' and i + 1 < len(args):
            try:
                lines = int(args[i+1])
                i += 2
            except ValueError:
                print_error("tail: invalid number of lines")
                return
        elif args[i].startswith('-'):
            print_error(f"tail: invalid option -- '{args[i][1:]}'")
            return
        else:
            files.append(args[i])
            i += 1

    for file in files:
        try:
            with open(file, 'r') as f:
                content = f.readlines()
                print(f"==> {file} <==")
                start = max(0, len(content) - lines)
                for line in content[start:]:
                    print(line, end='')
                print()
        except FileNotFoundError:
            print_error(f"tail: cannot open '{file}' for reading: No such file or directory")
        except IsADirectoryError:
            print_error(f"tail: error reading '{file}': Is a directory")
        except Exception as e:
            print_error(f"tail: {str(e)}")

def handle_wc(args):
    if not args:
        print_error("wc: missing file operand")
        return

    for file in args:
        try:
            with open(file, 'r') as f:
                lines = 0
                words = 0
                chars = 0
                for line in f:
                    lines += 1
                    words += len(line.split())
                    chars += len(line)
                print(f"{lines}\t{words}\t{chars}\t{file}")
        except FileNotFoundError:
            print_error(f"wc: '{file}': No such file or directory")
        except IsADirectoryError:
            print_error(f"wc: '{file}': Is a directory")
        except Exception as e:
            print_error(f"wc: {str(e)}")

def handle_history():
    print("History functionality has been disabled")

def handle_grep(args):
    if len(args) < 1:
        print_error("grep: search pattern required")
        return

    pattern = args[0]
    files = args[1:] if len(args) > 1 else []

    if not files:
        try:
            for line in sys.stdin:
                if pattern in line:
                    print(line, end='')
        except KeyboardInterrupt:
            return
    else:
        for file in files:
            try:
                with open(file, 'r') as f:
                    for line in f:
                        if pattern in line:
                            print(f"{file}:{line}", end='')
            except FileNotFoundError:
                print_error(f"grep: {file}: No such file or directory")
            except IsADirectoryError:
                print_error(f"grep: {file}: Is a directory")
            except Exception as e:
                print_error(f"grep: {str(e)}")

def handle_neofetch():
    username = getpass.getuser().lower()
    hostname = socket.gethostname().lower()
    os_name = platform.system()
    os_version = platform.version()
    kernel = platform.release()
    shell = os.path.basename(os.getenv('SHELL', 'cmd.exe' if os.name == 'nt' else 'unknown'))
    cpu = platform.processor()

    if os.name == 'nt':
        try:
            import psutil
            memory = f"{round(psutil.virtual_memory().total / (1024.**3), 1)}GB"
        except:
            memory = "Unknown"
    else:
        memory = f"{round(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024.**3), 1)}GB" if hasattr(os, 'sysconf') else "Unknown"

    art = [
        "       _,met$$$$$gg.          ",
        "    ,g$$$$$$$$$$$$$$$P.       ",
        "  ,g$$P\"     \"\"\"\"Y$$.\".       ",
        " ,$$P'              `$$$.     ",
        "',$$P       ,ggs.     `$$b:   ",
        "`d$$'     ,$P\"'   .    $$$    ",
        " $$P      d$'     ,    $$P    ",
        " $$:      $$.   -    ,d$$'    ",
        " $$;      Y$b._   _,d$P'      ",
        " Y$$.    `.`\"Y$$$$P\"'        ",
        " `$$b      \"-.__              ",
        "  `Y$$b                        ",
        "   `Y$$.                      ",
        "     `$$b.                     "
    ]

    info = [
        f"{username}@{hostname}",
        f"OS: {os_name} {os_version}",
        f"Kernel: {kernel}",
        f"Shell: {shell}",
        f"CPU: {cpu}",
        f"Memory: {memory}",
        "", "", "", "", "", "", "", "" 
    ]

    result = []
    for i in range(len(art)):
        art_part = art[i]
        info_part = info[i] if i < len(info) else ""
        
        line = f"{TerminalColors.RED}{art_part}\033[0;37m{info_part}" 
        result.append(line)

    print("\n".join(result))

def handle_echo(args):
    text = " ".join(args)
    print(text)

def handle_date():
    now = datetime.now()
    print(now.strftime("%a %b %d %H:%M:%S %Z %Y"))

def handle_time(args):
    start_time = time_module.time()
    
    if not args:
        return
    
    try:
        subprocess.run(args, shell=True)
    except Exception as e:
        print_error(f"time: {str(e)}")
    
    end_time = time_module.time()
    elapsed = end_time - start_time
    print(f"\nreal\t{elapsed:.3f}s")

def handle_whoami():
    print(getpass.getuser())

def handle_uname(args):
    show_all = '-a' in args
    show_kernel = '-r' in args
    show_system = '-s' in args
    
    if not args or show_all:
        print(f"{platform.system()} {platform.node()} {platform.release()} {platform.version()} {platform.machine()}")
    elif show_kernel:
        print(platform.release())
    elif show_system:
        print(platform.system())
    else:
        print(platform.system())

def handle_df():
    if os.name == 'nt':
        try:
            import ctypes
            drives = []
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                if bitmask & 1:
                    drives.append(letter + ':')
                bitmask >>= 1
            
            print("Filesystem     1K-blocks    Used Available Use% Mounted on")
            for drive in drives:
                try:
                    total, used, free = shutil.disk_usage(drive)
                    percent = (used / total) * 100
                    print(f"{drive}            {total//1024:<11}{used//1024:<11}{free//1024:<11}{percent:.0f}%   /")
                except:
                    print(f"{drive}            -           -           -    -   /")
        except:
            print_error("df: failed to get disk usage information")
    else:
        try:
            subprocess.run(['df', '-h'])
        except:
            print_error("df: command not available")

def handle_du(args):
    path = args[0] if args else "."
    total_size = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                except:
                    continue
        
        print(f"{total_size//1024}\t{path}")
    except Exception as e:
        print_error(f"du: {str(e)}")

def handle_find(args):
    if len(args) < 2:
        print_error("find: missing arguments")
        return
    
    path = args[0]
    name = args[1]
    
    try:
        for root, dirs, files in os.walk(path):
            for file in files:
                if name in file:
                    print(os.path.join(root, file))
    except Exception as e:
        print_error(f"find: {str(e)}")

def handle_ps():
    try:
        if os.name == 'nt':
            output = subprocess.check_output(['tasklist'], shell=True).decode()
            print(output)
        else:
            subprocess.run(['ps', 'aux'])
    except:
        print_error("ps: failed to get process list")

def handle_yes(args):
    text = " ".join(args) if args else "y"
    try:
        while True:
            print(text)
    except KeyboardInterrupt:
        return

def handle_jobs():
    print("No job control in this shell")

def handle_free():
    try:
        if os.name == 'nt':
            import psutil
            mem = psutil.virtual_memory()
            print(f"              total        used        free      shared  buff/cache   available")
            print(f"Mem:    {mem.total//1024:11}{mem.used//1024:11}{mem.free//1024:11}{0:11}{0:11}{mem.available//1024:11}")
        else:
            subprocess.run(['free', '-h'])
    except:
        print_error("free: failed to get memory information")

def handle_rev(args):
    if not args:
        try:
            while True:
                line = input()
                print(line[::-1])
        except (KeyboardInterrupt, EOFError):
            return
    
    for file in args:
        try:
            with open(file, 'r') as f:
                for line in f:
                    print(line.strip()[::-1])
        except FileNotFoundError:
            print_error(f"rev: {file}: No such file or directory")
        except IsADirectoryError:
            print_error(f"rev: {file}: Is a directory")
        except Exception as e:
            print_error(f"rev: {file}: {str(e)}")

def handle_diff(args):
    if len(args) != 2:
        print_error("diff: need exactly two files to compare")
        return
    
    file1, file2 = args
    
    try:
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
            
            for i, (line1, line2) in enumerate(zip(lines1, lines2)):
                if line1 != line2:
                    print(f"{i+1}c{i+1}")
                    print(f"< {line1.strip()}")
                    print(f"> {line2.strip()}")
            
            if len(lines1) > len(lines2):
                for i in range(len(lines2), len(lines1)):
                    print(f"{i+1}d{i}")
                    print(f"< {lines1[i].strip()}")
            elif len(lines2) > len(lines1):
                for i in range(len(lines1), len(lines2)):
                    print(f"{i}a{i+1}")
                    print(f"> {lines2[i].strip()}")
    except FileNotFoundError as e:
        print_error(f"diff: {str(e)}")
    except Exception as e:
        print_error(f"diff: {str(e)}")

def handle_uptime():
    try:
        if os.name == 'nt':
            import psutil
            boot_time = psutil.boot_time()
            now = time_module.time()
            uptime_seconds = now - boot_time
        else:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0 or not parts:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
        print(f"up {' '.join(parts)}")
    except Exception as e:
        print_error(f"uptime: {str(e)}")

def handle_lscpu():
    try:
        if os.name != 'nt':
            print_error("lscpu: this command is Windows-only in this implementation")
            return

        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                processor = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                cores = winreg.QueryValueEx(key, "NumberOfCores")[0]
                threads = winreg.QueryValueEx(key, "NumberOfLogicalProcessors")[0]
                vendor = winreg.QueryValueEx(key, "VendorIdentifier")[0]
            
            is_64bit = 'PROGRAMFILES(X86)' in os.environ
            arch = "x86_64" if is_64bit else "x86"
            
            print(f"{'Architecture:':<20} {arch}")
            print(f"{'CPU op-mode(s):':<20} 32-bit, 64-bit")
            print(f"{'Vendor ID:':<20} {vendor}")
            print(f"{'CPU(s):':<20} {threads}")
            print(f"{'Model name:':<20} {processor}")
            print(f"{'CPU cores:':<20} {cores}")
            print(f"{'Threads per core:':<20} {threads // cores}")
        except Exception as e:
            try:
                import wmi
                c = wmi.WMI()
                for cpu in c.Win32_Processor():
                    print(f"{'Architecture:':<20} {'x86_64' if cpu.AddressWidth == '64' else 'x86'}")
                    print(f"{'CPU op-mode(s):':<20} 32-bit, 64-bit")
                    print(f"{'Vendor ID:':<20} {cpu.Manufacturer}")
                    print(f"{'CPU(s):':<20} {cpu.NumberOfLogicalProcessors}")
                    print(f"{'Model name:':<20} {cpu.Name}")
                    print(f"{'CPU cores:':<20} {cpu.NumberOfCores}")
                    print(f"{'Threads per core:':<20} {cpu.NumberOfLogicalProcessors // cpu.NumberOfCores}")
                    break
            except:
                print_error("lscpu: failed to get CPU info (install pywin32 or wmi module)")
    except Exception as e:
        print_error(f"lscpu: {str(e)}")

def handle_lsmem():
    try:
        if os.name == 'nt':
            import psutil
            mem = psutil.virtual_memory()
            print(f"Total:        {mem.total // (1024 * 1024)} MB")
            print(f"Used:         {mem.used // (1024 * 1024)} MB")
            print(f"Free:         {mem.free // (1024 * 1024)} MB")
            print(f"Available:    {mem.available // (1024 * 1024)} MB")
        else:
            meminfo = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    key, value = line.split(':', 1)
                    meminfo[key] = value.strip().split()[0]
            
            total = int(meminfo['MemTotal']) // 1024
            free = int(meminfo['MemFree']) // 1024
            available = int(meminfo.get('MemAvailable', meminfo['MemFree'])) // 1024
            used = total - free
            
            print(f"Total:        {total} MB")
            print(f"Used:         {used} MB")
            print(f"Free:         {free} MB")
            print(f"Available:    {available} MB")
    except Exception as e:
        print_error(f"lsmem: {str(e)}")

def handle_stat(args):
    if not args:
        print_error("stat: missing file operand")
        return
    
    for file in args:
        try:
            st = os.stat(file)
            print(f"  File: {file}")
            print(f"  Size: {st.st_size}\tBlocks: {st.st_blocks}\tIO Block: {4096}")
            print(f"Device: {st.st_dev}\tInode: {st.st_ino}")
            print(f"Access: {oct(st.st_mode)[-3:]}")
            print(f"Access: {datetime.fromtimestamp(st.st_atime)}")
            print(f"Modify: {datetime.fromtimestamp(st.st_mtime)}")
            print(f"Change: {datetime.fromtimestamp(st.st_ctime)}")
        except FileNotFoundError:
            print_error(f"stat: cannot stat '{file}': No such file or directory")
        except Exception as e:
            print_error(f"stat: {str(e)}")

def handle_file(args):
    if not args:
        print_error("file: missing file operand")
        return
    
    for file in args:
        try:
            if os.path.isdir(file):
                print(f"{file}: directory")
            elif os.path.isfile(file):
                ext = os.path.splitext(file)[1].lower()
                if ext in ('.txt', '.log', '.md'):
                    print(f"{file}: ASCII text")
                elif ext in ('.py', '.sh', '.c', '.h', '.js'):
                    print(f"{file}: source code")
                elif ext in ('.jpg', '.jpeg', '.png', '.gif'):
                    print(f"{file}: image data")
                elif ext in ('.pdf', '.doc', '.docx'):
                    print(f"{file}: document")
                else:
                    print(f"{file}: regular file")
            elif os.path.islink(file):
                print(f"{file}: symbolic link")
            else:
                print(f"{file}: unknown type")
        except Exception as e:
            print_error(f"file: {str(e)}")

def handle_bc():
    print("Simple calculator. Enter 'quit' to exit.")
    while True:
        try:
            expr = input("> ")
            if expr.lower() == 'quit':
                break
            
            allowed_chars = set('0123456789+-*/(). ')
            if any(c not in allowed_chars for c in expr):
                print("Error: Only basic arithmetic operations allowed")
                continue
            
            try:
                result = eval(expr)
                print(result)
            except:
                print("Error: Invalid expression")
        except (KeyboardInterrupt, EOFError):
            print()
            break

def handle_lshw():
    try:
        import wmi
        import platform
        
        print(f"{TerminalColors.YELLOW}HARDWARE INFORMATION (GPU){TerminalColors.RESET}")
        print(f"{'-' * 60}")

        system_info = platform.uname()

        c = wmi.WMI()

        print(f"{TerminalColors.CYAN}System:{TerminalColors.RESET}")
        print(f"  {TerminalColors.WHITE}Node Name:{TerminalColors.RESET} {system_info.node}")
        print(f"  {TerminalColors.WHITE}OS:{TerminalColors.RESET} {system_info.system} {system_info.release}")
        print(f"  {TerminalColors.WHITE}Architecture:{TerminalColors.RESET} {platform.machine()}")
        print()

        print(f"{TerminalColors.CYAN}Display Adapters:{TerminalColors.RESET}")
        
        gpu_count = 0
        for gpu in c.Win32_VideoController():
            gpu_count += 1
            print(f"  {TerminalColors.GREEN}*-{TerminalColors.RESET}display{TerminalColors.RESET}")
            print(f"       {TerminalColors.WHITE}description:{TerminalColors.RESET} {gpu.Description}")
            print(f"       {TerminalColors.WHITE}product:{TerminalColors.RESET} {gpu.Name}")
            print(f"       {TerminalColors.WHITE}vendor:{TerminalColors.RESET} {gpu.AdapterCompatibility}")
            print(f"       {TerminalColors.WHITE}driver version:{TerminalColors.RESET} {gpu.DriverVersion}")
            print(f"       {TerminalColors.WHITE}memory:{TerminalColors.RESET} {int(gpu.AdapterRAM)/1024/1024:.0f} MB" if gpu.AdapterRAM else "       memory: N/A")
            print(f"       {TerminalColors.WHITE}resolution:{TerminalColors.RESET} {gpu.CurrentHorizontalResolution}x{gpu.CurrentVerticalResolution}" 
                  if gpu.CurrentHorizontalResolution else "       resolution: N/A")
            
        if gpu_count == 0:
            print(f"  {TerminalColors.RED}No display adapters found{TerminalColors.RESET}")
            
        print(f"\n{TerminalColors.YELLOW}Legend:{TerminalColors.RESET}")
        print(f"  [*] - Enabled device")
        print(f"{'-' * 60}")
        
    except ImportError:
        print_error("lshw: requires 'wmi' package (pip install wmi)")
    except Exception as e:
        print_error(f"lshw: {str(e)}")

def main():
    while True:
        try:
            user_input = input(get_prompt()).strip()
            if not user_input:
                continue
            
            parts = user_input.split()
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            if cmd == "ls":
                handle_ls()
            elif cmd == "cd":
                path = " ".join(args) if args else ""
                handle_cd(path)
            elif cmd == "pwd":
                handle_pwd()
            elif cmd == "mkdir":
                handle_mkdir(args)
            elif cmd == "rmdir":
                handle_rmdir(args)
            elif cmd == "cat":
                handle_cat(args)
            elif cmd == "touch":
                handle_touch(args)
            elif cmd == "rm":
                handle_rm(args)
            elif cmd == "cp":
                handle_cp(args)
            elif cmd == "mv":
                handle_mv(args)
            elif cmd == "less":
                handle_less(args)
            elif cmd == "tree":
                handle_tree(args[0] if args else ".")
            elif cmd == "head":
                handle_head(args)
            elif cmd == "tail":
                handle_tail(args)
            elif cmd == "wc":
                handle_wc(args)
            elif cmd == "history":
                handle_history()
            elif cmd == "grep":
                handle_grep(args)
            elif cmd == "cowsay":
                handle_cowsay(args)
            elif cmd == "clear":
                handle_clear()
            elif cmd == "neofetch":
                handle_neofetch()
            elif cmd == "echo":
                handle_echo(args)
            elif cmd == "date":
                handle_date()
            elif cmd == "time":
                handle_time(args)
            elif cmd == "whoami":
                handle_whoami()
            elif cmd == "uname":
                handle_uname(args)
            elif cmd == "df":
                handle_df()
            elif cmd == "du":
                handle_du(args)
            elif cmd == "find":
                handle_find(args)
            elif cmd == "ps":
                handle_ps()
            elif cmd == "yes":
                handle_yes(args)
            elif cmd == "jobs":
                handle_jobs()
            elif cmd == "free":
                handle_free()
            elif cmd == "rev":
                handle_rev(args)
            elif cmd == "diff":
                handle_diff(args)
            elif cmd == "uptime":
                handle_uptime()
            elif cmd == "lscpu":
                handle_lscpu()
            elif cmd == "lsmem":
                handle_lsmem()
            elif cmd == "stat":
                handle_stat(args)
            elif cmd == "file":
                handle_file(args)
            elif cmd == "bc":
                handle_bc()
            elif cmd == "lshw":
                handle_lshw()
            else:
                print_error(f"{cmd}: command not found")
                
        except (KeyboardInterrupt, EOFError):
            print("\033[0m", end="")
            break

if __name__ == "__main__":
    main()