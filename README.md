
# VS Code ESP-IDF Tools

This script allows for easy setup of ESP-IDF projects in VS Code, with full support for IntelliSense and IDF.

## Prerequisites

- Install the required python 3.7 packages using:
`pip install -r requirements.txt`
- Visual Studio Code
- Microsoft's C/C++ extension for VS Code
- WebFreak's Native Debug extension for VS Code

### Preparing VS Code environment

Run the following command to generate vscode tasks and configuration for Microsoft's C/C++ extension, and for WebFreak's Native Debug extension:

> `python vsc_idf.py generate --prjname [project name] --prjpath [path to project]`

You must either run the command in a terminal with ESP-IDF environment variables set, or you must provide a path to ESP-IDF using `--idfpath [path]` along with the rest of the command.

This will create a `c_cpp_properties.json`,  `tasks.json` and `launch.json` in the `.vscode` directory under the specified project path. These configuration files will require modification to reflect your setup.

Once the project is opened in VS Code, you will be able to run tasks using the Command Palette. You will also be able debug a device through VS Code by running the `ESP-IDF: OpenOCD` task and attaching GDB to it through VS Code using `ESP-IDF: Attach Debugger` under Debug. More information can be found below.

Currently it is recommended to build the project using ESP-IDF just once *before* running the generate command to ensure all paths are discovered. This behaviour may change in future versions of this script.

### Available tasks

The generated `tasks.json` provides the following tasks which can be executing the Command Palette in VS Code. They automatically set up the environment so no configuration is required.

- ESP-IDF: Build
   > Builds the application, along with all the required components and bootloader using ESP-IDF's idf.py.
- ESP-IDF: Clean
   > Cleans any output in the `build` directory using ESP-IDF's idf.py.
- ESP-IDF: Watch 'sdkconfig'
   > Waits for any changes to be made to the `sdkconfig` file and automatically generates a `sdkconfig.h` in the `build/config` directory.
- ESP-IDF: Flash
   > Flashes a device using ESP-IDF's idf.py. The device's port (`--devport`) must be configured in `tasks.json` in the `.vscode` directory.
- ESP-IDF: Monitor
   > Open's a serial monitor to communicate with the device using ESP-IDF's idf.py. The device's port and baud rate (`--devport`, `--devbaud`) must be configured in `tasks.json` in the `.vscode` directory.
- ESP-IDF: OpenOCD
   > Launches an OpenOCD instance to connect to the target device. The interface and target board scripts (`--ifscript`, `--bscript`) must be configured in `tasks.json` in the `.vscode` directory.
