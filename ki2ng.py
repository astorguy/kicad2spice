"""initialize and run Kicad cli to generate Ngspice netlist"""

from pathlib import Path
from subprocess import CompletedProcess
from typing import Any
import subprocess
import tomllib
import xml.etree.ElementTree as ET

# Constants


CONFIG_NAME: str = "ki2ng.toml"


class Key:
    """Keys for dictionaries. They can be referenced instead of using strings for keys.
    This is useful for avoiding typos and for IDE autocompletion.
    """

    GLOBAL: str = "GLOBAL"
    KICAD_CMD: str = "KICAD_CMD"
    PROJECT: str = "PROJECT"
    SCHEMATIC_LOC: str = "SCHEMATIC_LOC"
    SCHEMATIC_NAME: str = "SCHEMATIC_NAME"
    NETLIST_LOC: str = "NETLIST_LOC"
    NETLIST_NAME: str = "NETLIST_NAME"
    DEL_SLASHES: str = "DEL_SLASHES"
    DUT: str = "DUT"
    DEL_INCLUDES: str = "DEL_INCLUDES"
    DEL_MODELS: str = "DEL_MODELS"
    SVG_LOC: str = "SVG_LOC"
    SVG_NAME: str = "SVG_NAME"
    SVG_WIDTH: str = "SVG_WIDTH"


def read_config_file(config_name: str) -> dict[str, Any]:
    """Read the config file and return a config dictionary.
    The config file must be in the current working directory,
    or if not there, it must be in the script's directory.
    """
    CUR_WORK_DIR: Path = Path.cwd()  # current working directory
    SCRIPT_DIR: Path = Path(__file__).resolve().parent  # directory of this script

    config_file_in_cur_dir: Path = CUR_WORK_DIR / config_name
    if config_file_in_cur_dir.exists():
        with open(config_file_in_cur_dir, "rb") as file:
            config: dict[str, Any] = tomllib.load(file)
            print(f"Using config file: {config_file_in_cur_dir}")
            return config

    config_file_in_script_dir: Path = SCRIPT_DIR / config_name
    if config_file_in_script_dir.exists():
        with open(config_file_in_script_dir, "rb") as file:
            config: dict[str, Any] = tomllib.load(file)
            print(f"Using config file: {config_file_in_script_dir}")
            return config

    raise FileNotFoundError(
        f"Config file '{config_name}' not found in current or script directory."
    )


my_config: dict[str, Any] = read_config_file(CONFIG_NAME)

MY_PROJECT: str = my_config["GLOBAL"]["PROJECT"]  # set project section key
print(f"Project section referenced in {CONFIG_NAME}: [{MY_PROJECT}]")

# set these constants by reading the config file
KICAD: Path = Path(my_config[Key.GLOBAL][Key.KICAD_CMD])
SCH_LOC: Path = Path(my_config[MY_PROJECT][Key.SCHEMATIC_LOC])
SCH_FILENAME: Path = SCH_LOC / my_config[MY_PROJECT][Key.SCHEMATIC_NAME]
NETLIST_LOC: Path = Path(my_config[MY_PROJECT][Key.NETLIST_LOC])
NETLIST_FILENAME: Path = NETLIST_LOC / my_config[MY_PROJECT][Key.NETLIST_NAME]
DELETE_SLASHES: bool = my_config[MY_PROJECT][Key.DEL_SLASHES]
IS_DUT: bool = my_config[MY_PROJECT][Key.DUT]
DEL_INCLUDES: bool = my_config[MY_PROJECT][Key.DEL_INCLUDES]
DEL_MODELS: bool = my_config[MY_PROJECT][Key.DEL_MODELS]
SVG_LOC: Path = Path(my_config[MY_PROJECT][Key.SVG_LOC])
SVG_NAME: str = my_config[MY_PROJECT][Key.SVG_NAME]
SVG_FILENAME: Path = SVG_LOC / SVG_NAME
SVG_WIDTH: float = my_config[MY_PROJECT][Key.SVG_WIDTH]

# other constants
SCH_ROOT: str = SCH_FILENAME.stem
INITIAL_SVG_FILENAME: Path = SVG_LOC / f"{SCH_ROOT}.svg"


class KicadNetlist:
    """KiCad netlist export command"""

    def __init__(
        self, kicad_cmd: Path, sch_filename: Path, netlist_filename: Path
    ) -> None:
        self.kicad_cmd: Path = kicad_cmd
        self.sch_filename: Path = sch_filename
        self.netlist_filename: Path = netlist_filename

        # construct the command
        self.cmd_args = [f"{self.kicad_cmd}"]
        self.cmd_args.append("sch")
        self.cmd_args.append("export")
        self.cmd_args.append("netlist")
        self.cmd_args.append(f"--output")
        self.cmd_args.append(f"{self.netlist_filename}")
        self.cmd_args.append("--format")
        self.cmd_args.append("spice")
        self.cmd_args.append(f"{self.sch_filename}")
        self.cmd: str = " ".join(str(item) for item in self.cmd_args)

    def __str__(self) -> str:
        """print out the constructed KiCad cmd

        Returns:
            str: the cmd that has been contructed
        """
        return self.cmd

    def run(self) -> CompletedProcess[bytes]:
        """execute the kicad cmd"""
        return subprocess.run(self.cmd_args, check=False)

    def delete_forward_slashes(self) -> None:
        """Delete forward slashes from all node names in the netlist file."""

        # Open the file for reading and writing
        with open(self.netlist_filename, "r+") as file:
            lines = file.readlines()  # Read the lines
            file.seek(0)  # Move the file pointer back to the beginning

            # Iterate through each line
            for line in lines:
                # Check if the line starts with a letter
                if line[0].isalpha():
                    # Split the line into words
                    words = line.split()
                    # Remove the forward slash from each word that starts with it
                    words = [
                        word[1:] if word.startswith("/") else word for word in words
                    ]
                    # Join the words back together into a line
                    line = " ".join(words) + "\n"
                # Write the modified line back to the file
                file.write(line)

            # Truncate the file to the current position to remove any leftover content
            file.truncate()

    def delete_first_last_lines(self) -> None:
        """Delete the first and last lines of the netlist file."""
        with open(self.netlist_filename, "r+") as file:
            lines = file.readlines()
            file.seek(0)  # Move the file pointer back to the beginning

            # Skip the first and last lines and rewrite the file without them
            file.writelines(lines[1:-1])

            # Truncate the file to the current position to remove any leftover content
            file.truncate()

    def delete_lines_starting_with(self, prefix: str) -> None:
        """Delete lines in the netlist file that start with the specified prefix.
        Args:
            prefix (str): The prefix string to match at the beginning of lines.
        """
        with open(self.netlist_filename, "r+") as file:
            lines = file.readlines()
            file.seek(0)

            # Filter out the lines that start with the specified prefix
            lines = [
                line
                for line in lines
                if not line.strip().lower().startswith(prefix.lower())
            ]

            # Write the remaining lines back to the file
            file.writelines(lines)

            # Truncate the file to the current position to remove any leftover content
            file.truncate()

    def delete_include_lines(self) -> None:
        """Delete the .include lines in the netlist file."""
        self.delete_lines_starting_with(".include")

    def delete_model_lines(self) -> None:
        """Delete the .model lines in the netlist file."""
        self.delete_lines_starting_with(".model")


class KicadSvg:
    """KiCad svg export command"""

    def __init__(
        self, kicad_cmd: Path, sch_filename: Path, svg_directory: Path
    ) -> None:
        self.kicad_cmd: Path = kicad_cmd
        self.sch_filename: Path = sch_filename
        self.svg_directory: Path = svg_directory

        # construct the command
        self.cmd_args: list[str] = [f"{self.kicad_cmd}"]
        self.cmd_args.append("sch")
        self.cmd_args.append("export")
        self.cmd_args.append("svg")
        self.cmd_args.append("--output")
        self.cmd_args.append(f"{self.svg_directory}")  # output directory
        self.cmd_args.append("--exclude-drawing-sheet")
        self.cmd_args.append("--no-background-color")
        self.cmd_args.append(f"{self.sch_filename}")  # scheamtic file input
        self.cmd: str = " ".join(str(item) for item in self.cmd_args)

    def __str__(self) -> str:
        """print out the constructed KiCad cmd"""
        return self.cmd

    def run(self) -> CompletedProcess[bytes]:
        """execute the kicad cmd"""
        return subprocess.run(self.cmd_args, check=False)


class svg:
    """svg data is reprensented as a xml tree"""

    def __init__(self, svg_file: Path) -> None:
        self.data: ET.ElementTree = ET.parse(svg_file)

    def write_file(self, filename: Path) -> None:
        """write the svg data to a file"""
        self.data.write(filename, encoding="utf-8", xml_declaration=True)

    def scale(self, scale_factor: float) -> None:
        """scale the svg object by the scale factor"""
        root: ET.Element = self.data.getroot()
        width: float = float(root.attrib["width"][:-2]) * scale_factor
        height: float = float(root.attrib["height"][:-2]) * scale_factor
        root.attrib["width"] = f"{width}mm"
        root.attrib["height"] = f"{height}mm"

    def change_width(self, new_width: float) -> None:
        """change width of the svg object while maintaining aspect ratio"""
        root: ET.Element = self.data.getroot()
        scale_factor: float = new_width / float(root.attrib["width"][:-2])
        height: float = float(root.attrib["height"][:-2]) * scale_factor
        root.attrib["width"] = f"{new_width}mm"
        root.attrib["height"] = f"{height}mm"


def main() -> None:
    """main"""

    # create a netlist
    my_kicadnetlist = KicadNetlist(KICAD, SCH_FILENAME, NETLIST_FILENAME)
    print(
        f"\nKicad Netlist command:\n{my_kicadnetlist}\n"
    )  # print out the kicad cmd, though not necessary
    my_kicadnetlist.run()  # run the kicad cmd
    if DELETE_SLASHES:
        my_kicadnetlist.delete_forward_slashes()  # delete forward slashes in node names
    if IS_DUT:
        my_kicadnetlist.delete_first_last_lines()  # delete first & last lines of netlist
    if DEL_INCLUDES:
        my_kicadnetlist.delete_include_lines()  # delete the .include lines in the netlist
    if DEL_MODELS:
        my_kicadnetlist.delete_model_lines()  # delete the .model lines in the netlist
    print(f"Netlist file written: {NETLIST_FILENAME}")

    # create an svg
    if SVG_NAME:
        my_kicadsvg: KicadSvg = KicadSvg(KICAD, SCH_FILENAME, SVG_LOC)
        print(f"\nKicad SVG command:\n{my_kicadsvg}\n")  # print out the kicad cmd
        my_kicadsvg.run()  # run the kicad cmd
        my_svg: svg = svg(INITIAL_SVG_FILENAME)
        INITIAL_SVG_FILENAME.unlink()  # delete the initial svg file
        print(f"Initial SVG file deleted: {INITIAL_SVG_FILENAME}")
        my_svg.change_width(SVG_WIDTH)  # change the width of the svg
        my_svg.write_file(SVG_FILENAME)  # write the svg to a file
        print(f"SVG file written: {SVG_FILENAME}")


if __name__ == "__main__":
    main()
