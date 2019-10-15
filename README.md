
# VS Code ESP-IDF Tools

This script allows for easy setup of ESP-IDF projects in VS Code, with full support for IntelliSense and IDF functionality.

## Prerequisites

- Python 3.7 or newer
- Visual Studio Code
- Microsoft's C/C++ extension for VS Code
- WebFreak's Native Debug extension for VS Code

## Usage

### Preparing VS Code environment

Run the following command to generate configuration for VS Code tasks, Microsoft's C/C++ extension, and WebFreak's Native Debug extension:

> `python vsc_idf.py generate --prjname [project name] --prjpath [path to project]`

You must either run the command in a terminal with ESP-IDF environment variables set, or you must provide a path to ESP-IDF using `--idfpath [path]` along with the rest of the command.

This will create a `c_cpp_properties.json`,  `tasks.json` and `launch.json`, along with a `vsc_idf.json` in the `.vscode` directory under the specified project path. The `vsc_idf.json` configuration file will require modification to reflect your setup.

It is required to build the project to ensure the IntelliSense cache is built. This behaviour may change in future versions of this script.

### Debugging

Once the project is opened in VS Code, you will be able to run tasks using the Command Palette. You will also be able debug a device through VS Code by using `[GDB] Debug` under Debug. The `OpenOCD` task will start and the GDB client will connect to it automatically. Configuration of the debug interface in `.vscode/vsc_idf.json` in the project's directory is required prior to using the debugging features.

### Available tasks

The generated `tasks.json` provides the following tasks which can be executing the Command Palette in VS Code. They automatically set up the environment so no configuration is required.

- Build
   > Builds the application, along with all the required components and bootloader using ESP-IDF's idf.py. The output can be found in the project's `build` directory.
- Clean
   > Cleans any output in the project's `build` directory using ESP-IDF's idf.py.
- Monitor
   > Open's a serial monitor to communicate with the device using ESP-IDF's idf.py. The baud rate will automatically be determined based on what's specified in `sdkconfig`. The device's port (`device > port`) must be configured in `vsc_idf.json` in the project's `.vscode` directory.
- OpenOCD
   > Launches an OpenOCD instance to connect to the target device. The interface and target board scripts (`debug > interface`, `debug > board`) must be configured in `vsc_idf.json` in the project's `.vscode` directory.
- Upload
   > Builds and flashes a device using ESP-IDF's idf.py. The device's port (`device > port`) must be configured in `vsc_idf.json` in the project's `.vscode` directory.
- Upload and Monitor
   > Builds and flashes a device using ESP-IDF's idf.py. A monitor is then opened after the device has been flashed. The baud rate will automatically be determined based on what's specified in the `sdkconfig`. The device's port (`device > port`) must be configured in `vsc_idf.json` in the project's `.vscode` directory.
