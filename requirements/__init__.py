import subprocess

from importlib_metadata import metadata
from importlib_metadata import PackageNotFoundError
from pip_module_scanner.scanner import Scanner


# Override Scanner to skip dotfiles
class RepoImportScanner(Scanner):
    """Overwrite Scanner to use git tracked files instead of os.walk

    Also override init to create installed_packages since we just want to write package names
    """

    def __init__(self, *args, **kwargs):
        # overwrite libraries_installed keyed on package names
        super(RepoImportScanner, self).__init__(*args, **kwargs)
        self.installed_packages = [
            lib.key
            for lib in self.libraries_installed
            if lib.key not in "manageiq-integration-tests"
        ]  # ignore local

    def search_script_directory(self, path):
        """
        Recursively loop through a directory to find all python
        script files. When one is found, it is analyzed for import statements

        Only scans files tracked by git

        :param path: string
        :return: generator
        """
        proc = subprocess.Popen(["git", "ls-files", "--full-name"], stdout=subprocess.PIPE)
        proc.wait()
        # decode the file names because subprocess PIPE has them as bytes
        for file in [f.decode() for f in proc.stdout.read().splitlines()]:
            if (not file.endswith(".py")) or "sprout/" in file:
                continue  # skip sprout files and non-python files
            self.search_script_file(os.path.dirname(file), os.path.basename(file))

    def search_script(self, script):
        """
        Search a script's contents for import statements and check
        if they're currently prevent in the list of all installed
        pip modules.
        :param script: string
        :return: void
        """
        if self.import_statement.search(script):
            unique_found = []
            for f_import in set(self.import_statement.findall(script)):
                # Try the package metadata lookup, if its not found its just local or builtin
                try:
                    import_metadata = metadata(f_import)
                except PackageNotFoundError:
                    continue

                # Check that the package isn't already accounted for
                name = import_metadata["Name"]
                # Shriver - previously this was checking installed packages
                # Thinking this prevents freeze_all from working correctly on a clean venv
                # Want it to be able to go from clean venv + import scan to a frozen req file
                # freeze.py uses any existing frozen file as constraints
                if name not in self.libraries_found:  # and name in self.installed_packages:
                    unique_found.append(name)

            for package_name in unique_found:
                # Shriver - see above
                # self.installed_packages.remove(package_name)
                self.libraries_found.append(package_name)

    def output_to_fd(self, fd):
        """
        Outputs the results of the scanner to a file descriptor (stdout counts :)
        :param fd: file
        :return: void
        """
        for library in self.libraries_found:
            fd.write("{}\n".format(library))
