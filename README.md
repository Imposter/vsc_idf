
# VS Code ESP-IDF Tools

This script allows for easy setup of ESP-IDF projects in VS Code, with full support for IntelliSense and IDF.

## Instructions

Install the required python 3.7 packages using:
`pip install -r requirements.txt`

Available tool commands:
> You must either run these commands in a terminal with ESP-IDF environment variables set, or you must provide a path to ESP-IDF using `--idfpath [path]` along with the rest of the command

### Preparing VS Code environment

Run the following commands to generate vscode tasks and configuration for the C/C++:

> `python vsc_idf.py generate --prjname [project name] --prjpath [path to project]`

This will create a `c_cpp_properties.json` and `tasks.json` in the `.vscode` directory under the specified project path. Once the project is opened in VS Code, you will be able to run tasks using the Command Palette. Currently, it is recommended to build the project *before* running the generate command to ensure all paths are discovered.

### Available tasks

The generated `tasks.json` provides the following tasks which can be executing the Command Palette in VS Code. They automatically set up the environment so no configuration is required.

- ESP-IDF: Build
   > Builds the application, along with all the required components and bootloader using ESP-IDF's idf.py.
- ESP-IDF: Clean
   > Cleans any output in the `build` director using ESP-IDF's idf.py.
- ESP-IDF: Watch 'sdkconfig'
   > Waits for any changes to be made to the `sdkconfig` file and automatically generates a `sdkconfig.h` in the `build/config` directory 
- ESP-IDF: Flash
   > Flashes a device using ESP-IDF's idf.py. The device's port must be configured in `tasks.json` in the `.
