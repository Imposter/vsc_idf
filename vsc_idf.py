# The MIT License (MIT)
# Copyright (c) 2019 Imposter (github.com/imposter)
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
import time
import json
import subprocess as proc
from glob import glob
from os import path, walk, environ as env
from shutil import rmtree
from itertools import chain
from pprint import pprint
from argparse import ArgumentParser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
        return self._params[p]

    def generate_header(self):
        config_path = path.join(self._project_path, "build", "config")
        if path.exists(config_path):
            rmtree(config_path)
        with open(ensure_path(path.join(config_path, "sdkconfig.h")), "w") as f:
            output_lines = [ "Automatically generated! Do NOT edit!" ]
            for key, value in self._params.items():
                if value is 'y':
                    output_lines.append("#define {} 1".format(key))
                elif value is 'n' or not value:
                    pass
                else:
                    output_lines.append("#define {} {}".format(key, value))
            f.writelines(os.linesep.join(output_lines))

class SDKConfigWatchHandler(FileSystemEventHandler):
    def __init__(self, project_path):
        self._project_path = project_path

    def on_modified(self, event):
        if event.src_path == path.join(self._project_path, "sdkconfig"):
            config = SDKConfig(self._project_path)
            config.generate_header()

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
    def get_toolchain_bin_path():
        path_split = env["PATH"].split(os.pathsep)
        for p in path_split:
            if p.endswith(path.join("xtensa-esp32-elf", "bin")):
                return p
        return None

    @staticmethod
    def build_project(project_path):
        proc.run(["python", path.join(env["IDF_PATH"], "tools", "idf.py"), "build"], cwd=project_path)
    
    @staticmethod
    def clean_project(project_path):
        proc.run(["python", path.join(env["IDF_PATH"], "tools", "idf.py"), "clean"], cwd=project_path)

    @staticmethod
    def flash_device(project_path, com_port):
        proc.run(["python", path.join(env["IDF_PATH"], "tools", "idf.py"), "flash", "-p", com_port], cwd=project_path)

def operation_generate(args):
    script_path = path.abspath(__file__)
    project_name = args.prjname
    project_path = args.prjpath
    idf_path = env["IDF_PATH"]
    toolchain_bin = IDFTools.get_toolchain_bin_path()
    toolchain_root = path.normpath(path.join(toolchain_bin, ".."))
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
        IDFTools.get_component_include_paths(path.join(idf_path, "components")),
        
        # Project
        [ path.join(project_path, "build", "config") ],
        IDFTools.get_component_include_paths(path.join(project_path, "components")),
        [ path.join(project_path, "main") ]
    ]))

    # TODO: Move these into independent classes
    # Generate c_cpp_properties.json structure
    properties = {
        "configurations": [
            {
                "name": project_name, 
                "includePath": include_paths, 
                "browse": { 
                    "path": include_paths, 
                    "limitSymbolsToIncludedHeaders": True, 
                    "databaseFilename": "${workspaceFolder}/.vscode/browse.vc.db"
                },
                "defines": [ "DEBUG" ],
                "intelliSenseMode": "gcc-x86",
                "compilerPath": path.join(toolchain_bin, get_executable("xtensa-esp32-elf-gcc")),
                "compileCommands": "${workspaceFolder}/build/compile_commands.json"
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
                "label": "ESP-IDF: Build",
                "type": "shell",
                "group": "build",
                "problemMatcher": [],
                "command": "python \"{}\" --idfpath \"{}\" --prjpath \"{}\" --operation build".format(path.relpath(script_path, project_path), idf_path, project_path)
            },
            {
                "label": "ESP-IDF: Clean",
                "type": "shell",
                "group": "build",
                "problemMatcher": [],
                "command": "python \"{}\" --idfpath \"{}\" --prjpath \"{}\" --operation clean".format(path.relpath(script_path, project_path), idf_path, project_path)
            },
            {
                "label": "ESP-IDF: Watch 'sdkconfig'",
                "type": "shell",
                "group": "build",
                "problemMatcher": [],
                "command": "python \"{}\" --idfpath \"{}\" --prjpath \"{}\" --operation watch".format(path.relpath(script_path, project_path), idf_path, project_path)
            },
            {
                "label": "ESP-IDF: Flash Device",
                "type": "shell",
                "group": "build",
                "problemMatcher": [],
                "command": "python \"{}\" --idfpath \"{}\" --prjpath \"{}\" --operation flash".format(path.relpath(script_path, project_path), idf_path, project_path),
                "args": [
                    "--devport",
                    "DEVICE_PORT"
                ]
            }
        ]
    }

    # Write file
    with open(ensure_path(path.join(project_path, ".vscode", "tasks.json")), "w") as f:
        json.dump(tasks, f, indent=4)

    # Generate SDK config
    config = SDKConfig(project_path)
    config.generate_header()
    
    print("Done generating scripts and setting up vscode environment")

def operation_watch(args):
    event_handler = SDKConfigWatchHandler(args.prjpath)
    observer = Observer()
    observer.schedule(event_handler, args.prjpath)
    observer.start()
    try:
        print("Watching 'sdkconfig' for changes, press CTRL+C to exit")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def operation_build(args):
    IDFTools.build_project(args.prjpath)
    print("Done building project")

def operation_clean(args):
    IDFTools.clean_project(args.prjpath)
    print("Done cleaning project")

def operation_flash(args):
    IDFTools.flash_device(args.devport)
    print("Done flashing device")

def main():
    parser = ArgumentParser(description="vsc_idf.py - VS Code ESP-IDF Helper", prog=path.basename(sys.argv[0]))
    parser.add_argument("--operation",
                        type=str,
                        help="Operation to perform",
                        required=True)
    parser.add_argument("--prjpath",
                        type=str,
                        help="Project path",
                        required=True)
    parser.add_argument("--prjname",
                        type=str,
                        help="Project name",
                        required=False)
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
        env["IDF_PATH"] = args.idfpath

    # Initialize tools
    IDFTools.init()

    if args.operation == "generate":
        operation_generate(args)
    elif args.operation == "watch":
        operation_watch(args)
    elif args.operation == "build":
        operation_build(args)
    elif args.operation == "clean":
        operation_clean(args)
    elif args.operation == "flash":
        operation_flash(args)

if __name__ == "__main__":
    main()