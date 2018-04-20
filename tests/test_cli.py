from bcpc_build.cmd.main import cli as main_cli
from click.testing import CliRunner
import click
import os


def output_tail(output):
    return '\n'.join(output.split('\n')[1:])


def test_available_commands():
    command_output_tail = """
Options:
  --help  Show this message and exit.

Commands:
  bootstrap  Bootstraps a new build.
  db         Administers the database.
  init       Initializes the bcpc-build installation.
  unit       Manages build units.
"""
    runner = CliRunner()
    result = runner.invoke(main_cli)

    print(output_tail(result.output))
    print(command_output_tail)
    assert result.exit_code == 0
    assert output_tail(result.output) == command_output_tail


class TestBootstrapCommand:
    def test_usage(self):
        command_output_tail = """
  Bootstraps a new build.

Options:
  -c, --config-file FILENAME    Config file for bootstrap operation.
  --source-url TEXT             URL for build sources.
  --depends TEXT                Source dependency <name>:<url>
  --strategy [v7|v8]            Build strategy.
  --configure / --no-configure  Run the configuration phase.
  --build / --no-build          Run the build phase.
  --wait / --no-wait            Wait for bootstrap to complete in foreground.
  --help                        Show this message and exit.
"""
        runner = CliRunner()
        result = runner.invoke(main_cli, ['bootstrap', '--help'])
        assert result.exit_code == 0
        assert output_tail(result.output) == command_output_tail


class TestDbCommand:
    def test_usage(self):
        command_output_tail = """
  Administers the database.

Options:
  --help  Show this message and exit.

Commands:
  backup   Backup the database.
  console  Opens interactive console into database.
  import   Import the database.
  migrate  Migrates the database.
  setup    Setups up the database.
"""
        runner = CliRunner()
        result = runner.invoke(main_cli, ['db', '--help'])
        assert result.exit_code == 0
        assert output_tail(result.output) == command_output_tail


class TestInitCommand:
    def test_usage(self):
        command_output_tail = """
  Initializes the bcpc-build installation.

Options:
  --force  Force initial setup even if previously run.
  --help   Show this message and exit.
"""
        runner = CliRunner()
        result = runner.invoke(main_cli, ['init', '--help'])
        assert result.exit_code == 0
        assert output_tail(result.output) == command_output_tail


class TestUnitCommand:
    def test_usage(self):
        command_output_tail = """
  Manages build units.

Options:
  --help  Show this message and exit.

Commands:
  build    Initiate a build of a unit.
  config   Manages build unit configuration.
  destroy  Destroy build unit.
  list     List build units.
  modify   Modify build unit metadata
  shell    Start a shell in the build unit.
  show     Show build unit information.
"""
        runner = CliRunner()
        result = runner.invoke(main_cli, ['unit', '--help'])
        assert result.exit_code == 0
        assert output_tail(result.output) == command_output_tail

    class TestUnitBuildSubcommand:
        def test_usage(self):
            command_output_tail = """
  Initiate a build of a unit.

Options:
  --wait / --no-wait  Wait for build synchronously.
  --strategy [v7|v8]  Build strategy.  [required]
  --help              Show this message and exit.
"""
            runner = CliRunner()
            result = runner.invoke(main_cli, ['unit', 'build', '--help'])
            assert result.exit_code == 0
            assert output_tail(result.output) == command_output_tail

        def test_requires_id(self):
            command_output_tail = """
Error: Missing argument "id".
"""
            runner = CliRunner()
            result = runner.invoke(main_cli, ['unit', 'build'])
            assert result.exit_code == 2
            assert output_tail(result.output) == command_output_tail

    class TestUnitConfigSubcommand:
        def test_usage(self):
            command_output_tail = """
  Manages build unit configuration.

Options:
  --help  Show this message and exit.

Commands:
  edit  Edit current configuration.
  show  Show active configuration
  sync  Synchronizes configuration.
"""
            runner = CliRunner()
            result = runner.invoke(main_cli, ['unit', 'config', '--help'])
            assert result.exit_code == 0
            assert output_tail(result.output) == command_output_tail

    class TestUnitDestroySubcommand:
        def test_usage(self):
            command_output_tail = """
  Destroy build unit.

Options:
  --help  Show this message and exit.
"""
            runner = CliRunner()
            result = runner.invoke(main_cli, ['unit', 'destroy', '--help'])
            assert result.exit_code == 0
            assert output_tail(result.output) == command_output_tail

    class TestUnitListSubcommand:
        def test_usage(self):
            command_output_tail = """
  List build units.

Options:
  -f, --format TEXT  Listing format
  --long             List all fields
  --help             Show this message and exit.
"""
            runner = CliRunner()
            result = runner.invoke(main_cli, ['unit', 'list', '--help'])
            assert result.exit_code == 0
            assert output_tail(result.output) == command_output_tail

    class TestUnitModifySubcommand:
        def test_usage(self):
            command_output_tail = """
  Modify build unit metadata

Options:
  --set-state BUILDSTATE  Set build unit state.
  --help                  Show this message and exit.
"""
            runner = CliRunner()
            result = runner.invoke(main_cli, ['unit', 'modify', '--help'])
            assert result.exit_code == 0
            assert output_tail(result.output) == command_output_tail

    class TestUnitShellSubcommand:
        def test_usage(self):
            command_output_tail = """
  Start a shell in the build unit.

Options:
  --help  Show this message and exit.
"""
            runner = CliRunner()
            result = runner.invoke(main_cli, ['unit', 'shell', '--help'])
            assert result.exit_code == 0
            assert output_tail(result.output) == command_output_tail

    class TestUnitShowSubcommand:
        def test_usage(self):
            command_output_tail = """
  Show build unit information.

Options:
  --format TEXT  Display format
  --help         Show this message and exit.
"""
            runner = CliRunner()
            result = runner.invoke(main_cli, ['unit', 'show', '--help'])
            assert result.exit_code == 0
            assert output_tail(result.output) == command_output_tail
