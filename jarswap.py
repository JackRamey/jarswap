#!/usr/bin/env python3
import os
import re
import shutil
import argparse

CWD = os.getcwd()
HOME = os.path.expanduser('~')
IVY_CACHE = os.path.join(HOME, '.ivy2', 'cache')
BUILD_DIR = os.path.join(CWD, 'build', 'libs')

parser = argparse.ArgumentParser()
parser.add_argument('package', help='The package that the jar is delivered in.')
parser.add_argument('project', help='The name of the project.')
parser.add_argument('-f', '--force', action='store_true',
                    help="Forces creating a backup, even if one already exists. WARNING: this will destroy the "
                         "existing backup")
parser.add_argument('-R', '--restore', action='store_true',
                    help="Restore the latest backup.")
parser.add_argument('--build', metavar='build', type=str, nargs='?', default=BUILD_DIR,
                    help="Specify a directory where the build jar will be located. "
                         "The default is {}".format(BUILD_DIR))
parser.add_argument('--cache', metavar='cache', type=str, nargs='?', default=IVY_CACHE,
                    help="Specify a directory which will be used as the cache instead of the default ivy2 cache. "
                         "The default is {}".format(IVY_CACHE))
args = parser.parse_args()


class JarFileFactory:
    @staticmethod
    def create_jar_file(filename):
        parsed_filename = JarFileFactory._parse_filename(filename)
        if parsed_filename is not None:
            return parsed_filename

    @staticmethod
    def _parse_filename(filename):
        matches = re.search('(.*)-([0-9.]*)(\.jar|\.jar\.bak)$', filename)
        if matches:
            groups = matches.groups()
            return JarFile(filename, groups[0], groups[1], groups[2])
        else:
            return None


class JarFile:
    def __init__(self, filename, basename, version, extension):
        self.filename = filename
        self.basename = self.extract_basename()
        self.version = self.extract_version()
        self.extension = self.extract_extension()

    def __lt__(self, other):
        version_components = self.version.split('.')
        other_version_components = other.version.split('.')
        for counter, component in enumerate(version_components):
            other_component = other_version_components[counter]
            if int(component) != int(other_component):
                return int(component) < int(other_component)
        return False

    def __str__(self):
        return self.filename

    def create_backup(self, directory, force):
        if os.path.isfile(os.path.join(directory, self.construct_backup_filename())) and not force:
            print('Backup for this project and package already exists. '
                  'Will not create a new backup, overwriting existing jar.')
            return
        original_path = os.path.join(directory, self.filename)
        backup_path = os.path.join(directory, self.filename + '.bak')
        print('Creating backup: {}'.format(backup_path))
        shutil.move(original_path, backup_path)

    def restore_from_backup(self, directory):
        if not os.path.isfile(os.path.join(directory, self.construct_backup_filename())):
            print('No backup exists for jar: '.format(self.construct_backup_filename()))
            exit(1)
        original_path = os.path.join(directory, self.construct_filename())
        backup_path = os.path.join(directory, self.construct_backup_filename())
        print('Replacing current file [{}] with backup [{}]'.format(original_path, backup_path))
        shutil.move(backup_path, original_path)

    def copy(self, source, destination):
        source_path = os.path.join(source, self.filename)
        destination_path = os.path.join(destination, self.construct_filename())
        print('Copying file from {} to {}'.format(source_path, destination_path))
        shutil.copy(source_path, destination_path)

    def construct_backup_filename(self):
        return self.basename + '-' + self.version + '.jar.bak'

    def construct_filename(self):
        return self.basename + '-' + self.version + '.jar'

    def extract_basename(self):
        return self._parse_filename()[0]

    def extract_version(self):
        return self._parse_filename()[1]

    def extract_extension(self):
        return self._parse_filename()[2]

    def is_backup(self):
        return self.extension == '.jar.bak'

    def _parse_filename(self):
        matches = re.search('(.*)-([0-9.]*)(\.jar|\.jar\.bak)$', self.filename)
        if matches:
            return matches.groups()
        else:
            return None


def find_latest_jar(package: str, project: str) -> JarFile:
    print('Finding latest jar for {}.{}'.format(package, project))
    package_path = os.path.join(IVY_CACHE, package)
    project_path = os.path.join(package_path, project)
    jar_path = os.path.join(project_path, 'jars')
    if not os.path.isdir(package_path):
        print('Could not find package cache for {}'.format(package))
    if not os.path.isdir(project_path):
        print('Could not find project [{}] in package [{}]'.format(project, package))
    if not os.path.isdir(jar_path):
        print('Could not find jars directory within project path: {}'.format(project_path))
    jars = filter(None, map(JarFileFactory.create_jar_file, os.listdir(jar_path)))
    return max(jars)


def get_latest_build_jar(build_dir: str) -> JarFile:
    print('Searching for latest jar in: {}'.format(build_dir))
    pattern = '(.*)-([0-9.]*)\.jar$'
    jars = filter(lambda file: re.match(pattern, file), os.listdir(build_dir))
    jar_files = filter(None, map(JarFileFactory.create_jar_file, jars))
    return max(jar_files)


# Check all files and directories exist needed for this script to run.
def check_files_and_directories(cache_dir):
    return is_directory(cache_dir)


def is_file(file):
    check = os.path.isfile(file)
    if not check:
        print("File -> '{}' not found.".format(file))
    return check


def is_directory(directory):
    check = os.path.isdir(directory)
    if not check:
        print("messageDirectory -> '{}' not found.".format(directory))
    return check


def create_backup_and_replace(cache_dir, build_dir, package, project, force):
    latest_jar = get_latest_build_jar(build_dir)
    if not latest_jar:
        print('Could not find latest build.')
        exit(1)
    current_jar = find_latest_jar(package, project)
    if not current_jar:
        print('Could not find latest jar for {} {}'.format(package, project))
        exit(1)
    latest_jar.basename = current_jar.basename
    latest_jar.version = current_jar.version

    source = build_dir
    destination = os.path.join(cache_dir, package, project, 'jars')

    current_jar.create_backup(destination, force)
    latest_jar.copy(source, destination)


def restore_latest_backup(cache_dir, package, project):
    destination = os.path.join(cache_dir, package, project, 'jars')
    latest_jar = find_latest_jar(package, project)
    latest_jar.restore_from_backup(destination)

if __name__ == "__main__":

    cache = os.path.expanduser(args.cache)
    build = os.path.expanduser(args.build)

    if not check_files_and_directories(cache):
        exit(1)
    if not is_directory(build):
        exit(1)

    if not args.restore:
        create_backup_and_replace(cache, build, args.package, args.project, args.force)
    else:
        restore_latest_backup(cache, args.package, args.project)

