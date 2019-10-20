# The MIT License (MIT)
# Copyright (c) 2019 Eyaz Rehman (github.com/imposter)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import os
import signal
import time
import json
import re
import subprocess as proc
from glob import glob
from os import path, walk, environ as env
from shutil import rmtree
from itertools import chain
from pprint import pprint
from argparse import ArgumentParser

# Utility
def get_executable(name):
    if os.name == "nt":
        return name + ".exe"
    return name

def ensure_path(p):
    p_dir = path.dirname(p)
    if not path.exists(p_dir):
        os.makedirs(p_dir)
    return p

class SDKConfig:
    def __init__(self, project_path):
        self._project_path = project_path
        self._params = dict()
        with open(path.join(project_path, "sdkconfig"), "r") as f:
            for line in f.read().splitlines():
                if (line.startswith("#")):
                    continue
                split_line = line.split("=")
                if len(split_line) == 2:
                    self._params[split_line[0]] = split_line[1]

    def param(self, p):
        if p in self._params:
            return self._params[p]
        return None

    def generate_header(self):
        config_path = path.join(self._project_path, "build", "config")
        if path.exists(config_path):
            rmtree(config_path)
        with open(ensure_path(path.join(config_path, "sdkconfig.h")), "w") as f:
            output_lines = [ "// Automatically generated! Do NOT edit!" ]
            for key, value in self._params.items():
                if value is 'y':
                    output_lines.append("#define {} 1".format(key))
                elif value is 'n' or not value:
                    pass
                else:
                    output_lines.append("#define {} {}".format(key, value))
            f.writelines(os.linesep.join(output_lines))

class IDFTools:
    INCLUDED_EXTS = [ ".h", ".hpp" ]
    EXCLUDED_EXTS = [ ".c", ".cpp" ]
    EXCLUDED_FILES = [ "sdkconfig.h" ]

    @staticmethod
    def init():
        out = proc.check_output([ "python", path.join(env["IDF_PATH"], "tools", "idf_tools.py"), "export", "--format", "key-value" ]).decode("UTF-8").rstrip()
        for p in out.splitlines():
            split_path = p.split("=")
            env[split_path[0]] = split_path[1]

    @staticmethod
    def get_component_include_paths(root_path):
        includes = set()
        for dir_path, dir_names, file_names in walk(root_path):
            for d in dir_names:
                d_path = path.join(dir_path, d)
                d_inc = IDFTools.get_include_paths(d_path)
                if len(d_inc) > 0:
                    includes.add(d_path)
                    includes.union(d_inc)
        return sorted(includes)

    @staticmethod
    def get_include_paths(root_path):
        search_path = root_path + "/**/*" + "".join(list("[{}]".format(ext) for ext in IDFTools.INCLUDED_EXTS))
        files = glob(search_path, recursive=True)
        temp_dirs = set([ path.dirname(f) for f in files ])
        excluded_dirs = set()
        for p in temp_dirs:
            for dir_path, dir_names, file_names in walk(p):
                for f in file_names:
                    file_path = path.join(dir_path, f)
                    file_name, file_ext = path.splitext(file_path)
                    if not file_ext:
                        continue
                    if f in IDFTools.EXCLUDED_FILES or file_ext in IDFTools.EXCLUDED_EXTS:
                        excluded_dirs.add(dir_path)

        included_dirs = temp_dirs - excluded_dirs

        return included_dirs

    @staticmethod
    def get_tool_path(tool):
        with open(path.join(env["IDF_PATH"], "tools", "tools.json"), "r") as f:
            obj = json.load(f)
            for t in obj["tools"]:
                if t["name"] == tool:
                    for v in t["versions"]:
                        if "status" in v and v["status"] == "recommended":
                            return path.join(env["IDF_TOOLS_PATH"], "tools", tool, v["name"])
        return None

    @staticmethod
    def get_current_toolchain_version():
        with open(path.join(env["IDF_PATH"], "tools", "toolchain_versions.mk"), "r") as f:
            lines = f.readlines()
            for line in lines:
                split_line = [ l.strip() for l in line.split("=") ]
                if len(split_line) != 2:
                    continue
                if split_line[0] == "CURRENT_TOOLCHAIN_GCC_VERSION":
                    return split_line[1]
        return None

    @staticmethod
    def get_project_name(project_path):
        with open(path.join(project_path, "CMakeLists.txt"), "r") as f:
            lines = f.readlines()
            for line in lines:
                res = re.search("(.+)\((.+)\)", line)
                if res:
                    func = res.group(1)
                    params = res.group(2)
                    if func == "project":
                        return params
        return None

    @staticmethod
    def config_project(project_path):
        proc.run([
            "python", 
            path.join(env["IDF_PATH"], "tools", "idf.py"), 
            "menuconfig"
        ], cwd=project_path)

    @staticmethod
    def build_project(project_path):
        proc.run([
            "python", 
            path.join(env["IDF_PATH"], "tools", "idf.py"), 
            "build"
        ], cwd=project_path)
    
    @staticmethod
    def clean_project(project_path):
        proc.run([
            "python", 
            path.join(env["IDF_PATH"], "tools", "idf.py"), 
            "clean"
        ], cwd=project_path)

    @staticmethod
    def flash_device(project_path, com_port):
        proc.run([
            "python", 
            path.join(env["IDF_PATH"], "tools", "idf.py"), 
            "flash", 
            "-p", com_port
        ], cwd=project_path)

    @staticmethod
    def monitor_device(project_path, com_port):
        proc.run([
            "python", 
            path.join(env["IDF_PATH"], "tools", "idf.py"), 
            "monitor", 
            "-p", com_port
        ], cwd=project_path)

    @staticmethod
    def debug_device(interface_script, board_script):
        openocd_root = path.join(IDFTools.get_tool_path("openocd-esp32"), "openocd-esp32")
        openocd_bin = path.join(openocd_root, "bin")
        openocd_scripts = path.join(openocd_root, "share", "openocd", "scripts")
        proc.run([
            path.join(openocd_bin, get_executable("openocd")), 
            "-s", openocd_scripts,
            "-f", path.join(openocd_scripts, "interface", interface_script),
            "-f", path.join(openocd_scripts, "board", board_script)
        ])

def operation_generate(args):
    script_path = path.abspath(__file__)
    project_path = path.abspath(args.prjpath)
    project_name = IDFTools.get_project_name(project_path)
    idf_path = env["IDF_PATH"]
    toolchain_root =  path.join(IDFTools.get_tool_path("xtensa-esp32-elf"), "xtensa-esp32-elf")
    toolchain_bin = path.join(toolchain_root, "bin")
    toolchain_version = IDFTools.get_current_toolchain_version()
    toolchain_lib = path.join(toolchain_root, "lib", "gcc", "xtensa-esp32-elf", toolchain_version)
   
    # Gather include paths
    include_paths = list(chain.from_iterable([
        # Toolchain includes
        [
            path.join(toolchain_root, "xtensa-esp32-elf", "include"),
            path.join(toolchain_root, "xtensa-esp32-elf", "include", "c++", toolchain_version),
            path.join(toolchain_root, "xtensa-esp32-elf", "include", "c++", toolchain_version, "xtensa-esp32-elf"),
            path.join(toolchain_lib, "include"),
            path.join(toolchain_lib, "include-fixed")
        ],

        # ESP-IDF components
        [ path.join(idf_path, "components", "**") ],
        #IDFTools.get_component_include_paths(path.join(idf_path, "components")),
        
        # Project
        [ path.join(project_path, "build", "config") ],
        IDFTools.get_component_include_paths(path.join(project_path, "components")),
        [ path.join(project_path, "main") ]
    ]))

    # Generate SDK config
    sdk_config = SDKConfig(project_path)
    sdk_config.generate_header()

    # Generate c_cpp_properties.json structure
    properties = {
        "configurations": [
            {
                "name": project_name,
                "includePath": include_paths, 
                "browse": { 
                    "path": include_paths, 
                    "limitSymbolsToIncludedHeaders": True, 
                    "databaseFilename": path.join(project_path, ".vscode", "browse.vc.db")
                },
                "defines": [],
                "intelliSenseMode": "gcc-x86",
                "compilerPath": path.join(toolchain_bin, get_executable("xtensa-esp32-elf-gcc")),
                "compileCommands": path.join(project_path, "build", "compile_commands.json")
            }
        ],
        "version": 4
    }

    # Write file
    with open(ensure_path(path.join(project_path, ".vscode", "c_cpp_properties.json")), "w") as f:
        json.dump(properties, f, indent=4)

    # Generate tasks.json
    tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                **{
                    "label": label,
                    "type": "shell",
                    "group": "build",
                    "command": "python",
                    "args": [
                        script_path,
                        "--idfpath", idf_path,
                        "--prjpath", project_path,
                        "--operations", ",".join(body["operations"])
                    ]
                }, 
                **(body["params"] if "params" in body else {})
            } for label, body in {
                "Config": { "operations": [ "config" ] },
                "Build": { "operations": [ "build" ] }, 
                "Clean": { "operations": [ "clean" ] }, 
                "Monitor": { "operations": [ "monitor" ] },
                "OpenOCD": { 
                    "operations": [ "debug" ], 
                    "params": {
                        "isBackground": True,
                        "problemMatcher": [
                            {
                                "pattern":[
                                    {
                                        "regexp": "^(Info |Warn ):(.*)$",
                                        "severity": 1,
                                        "message": 2,
                                        "file": 1, # compat
                                        "kind": "file"
                                    }
                                ],
                                "background": {
                                    "activeOnStart": True,
                                    "beginsPattern": ".+",
                                    "endsPattern": "Info : Listening on port \\d+ for gdb connections",
                                }
                            }
                        ]
                    } 
                },
                "Upload": { "operations": [ "build", "flash" ] },
                "Upload and Monitor": { "operations": [ "build", "flash", "monitor" ] },
            }.items()
        ]
    }

    # Write file
    with open(ensure_path(path.join(project_path, ".vscode", "tasks.json")), "w") as f:
        json.dump(tasks, f, indent=4)
    
    # Generate launch.json
    launch = {
        "version": "0.2.0",
        "configurations": [
            {
                "type": "gdb",
                "request": "attach",
                "name": "[GDB] Debug",
                "executable": path.join(project_path, "build", project_name + ".elf"),
                "gdbpath": path.join(toolchain_bin, get_executable("xtensa-esp32-elf-gdb")),
                "target": ":3333",
                "remote": True,
                "cwd": project_path,
                "valuesFormatting": "parseText",
                "preLaunchTask": "OpenOCD",
                "autorun": [
                    "target remote localhost:3333",
                    "monitor reset halt",
                    "set remote hardware-breakpoint-limit 2",
                    "flushregs",
                    "hbreak app_main",
                    "continue"
                ]
            }
        ]
    }

    # Windows patch: https://bbs.esp32.com/viewtopic.php?t=12479
    if os.name == "nt":
        launch["configurations"][0]["env"] = {
            "TERM": "xterm"
        }

    # Write file
    with open(ensure_path(path.join(project_path, ".vscode", "launch.json")), "w") as f:
        json.dump(launch, f, indent=4)

    # Default configuration, only generated if a configuration isn't already present
    config_path = ensure_path(path.join(project_path, ".vscode", "vsc_idf.json"))
    if not path.exists(config_path):
        config = {
            "device": {
                "port": "COM3" if os.name == "nt" else "/dev/ttyUSB0"
            },
            "debug": {
                "interface": path.join("ftdi", "esp32_devkitj_v1.cfg"),
                "board": "esp32-wrover.cfg"
            }
        }

        # Write file
        with open(ensure_path(path.join(project_path, ".vscode", "vsc_idf.json")), "w") as f:
            json.dump(config, f, indent=4)
            
        print("Make sure to update '.vscode/vsc_idf.json' in the project directory")

    print("Done generating scripts and setting up vscode environment")

def operation_config(args):
    IDFTools.config_project(args.prjpath)

def operation_build(args):
    IDFTools.build_project(args.prjpath)

def operation_clean(args):
    IDFTools.clean_project(args.prjpath)

def operation_flash(args):
    with open(path.join(args.prjpath, ".vscode", "vsc_idf.json"), "r") as f:
        config = json.load(f)
        IDFTools.flash_device(args.prjpath, config["device"]["port"])

def operation_monitor(args):
    with open(path.join(args.prjpath, ".vscode", "vsc_idf.json"), "r") as f:
        config = json.load(f)
        device = config["device"]
        IDFTools.monitor_device(args.prjpath, device["port"])

def operation_debug(args):
    with open(path.join(args.prjpath, ".vscode", "vsc_idf.json"), "r") as f:
        config = json.load(f)
        debug = config["debug"]
        IDFTools.debug_device(debug["interface"], debug["board"])

def main():
    parser = ArgumentParser(description="vsc_idf.py - VS Code ESP-IDF Helper", prog=path.basename(sys.argv[0]))
    parser.add_argument("--operations",
                        type=str,
                        help="Operations to perform, multiple can be seperated using commas",
                        required=True)
    parser.add_argument("--prjpath",
                        type=str,
                        help="Project path",
                        required=True)
    parser.add_argument("--idfpath",
                        type=str,
                        help="ESP-IDF path",
                        required=False)
    
    args = parser.parse_args()

    # Ensure environment is set up correctly
    if "IDF_PATH" not in env and not args.idfpath:
        raise Exception("Environment variable 'IDF_PATH' nor 'idfpath' argument was provided! Run platform-specific environment setup script or set 'idfpath'")
    
    # IDF path argument overrides environment variables
    if args.idfpath:
        env["IDF_PATH"] = path.abspath(args.idfpath)

    # Initialize tools
    IDFTools.init()

    # Split operations
    operations = args.operations.split(",")

    for operation in operations:
        if operation == "generate":
            operation_generate(args)
        elif operation == "config":
            operation_config(args)
        elif operation == "build":
            operation_build(args)
        elif operation == "clean":
            operation_clean(args)
        elif operation == "flash":
            operation_flash(args)
        elif operation == "monitor":
            operation_monitor(args)
        elif operation == "debug":
            operation_debug(args)

if __name__ == "__main__":
    main()