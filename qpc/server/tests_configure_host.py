"""Test the CLI module."""

import sys
import unittest

from qpc import messages
from qpc.cli import CLI
from qpc.tests_utilities import HushUpStderr
from qpc.utils import read_server_config, write_server_config

DEFAULT_PORT = 9443


class ConfigureHostTests(unittest.TestCase):
    """Class for testing the server host configuration."""

    def setUp(self):
        """Create test setup."""
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        sys.stderr = HushUpStderr()

    def tearDown(self):
        """Remove test case setup."""
        # Reset server config to default ip/port
        sys.argv = [
            "/bin/qpc",
            "server",
            "config",
            "--host",
            "127.0.0.1",
            "--port",
            str(DEFAULT_PORT),
        ]

        with self.assertLogs(level="INFO") as log:
            CLI().main()
            config = read_server_config()
            self.assertEqual(config["host"], "127.0.0.1")
            self.assertEqual(config["port"], DEFAULT_PORT)
            expected_message = messages.SERVER_CONFIG_SUCCESS % {
                "protocol": "https", "host": "127.0.0.1", "port": str(DEFAULT_PORT)
            }
            self.assertIn(expected_message, log.output[-1])
        # Restore stderr
        sys.stderr = self.orig_stderr

    def test_config_host_req_args_err(self):
        """Testing the configure server requires host arg."""
        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "server", "config"]
            CLI().main()

    def test_config_host_alpha_port_err(self):
        """Testing the configure server requires bad port."""
        with self.assertRaises(SystemExit):
            sys.argv = [
                "/bin/qpc",
                "server",
                "config",
                "--host",
                "127.0.0.1",
                "--port",
                "abc",
            ]
            CLI().main()

    def test_success_config_server(self):
        """Testing the configure server green path."""
        sys.argv = [
            "/bin/qpc",
            "server",
            "config",
            "--host",
            "127.0.0.1",
            "--port",
            "8005",
        ]
        with self.assertLogs(level="INFO") as log:
            CLI().main()
            config = read_server_config()
            self.assertEqual(config["host"], "127.0.0.1")
            self.assertEqual(config["port"], 8005)
            expected_message = messages.SERVER_CONFIG_SUCCESS % {
                "protocol": "https", "host": "127.0.0.1", "port": "8005"
            }
            self.assertIn(expected_message, log.output[-1])

    def test_config_server_default_port(self):
        """Testing the configure server default port."""
        sys.argv = ["/bin/qpc", "server", "config", "--host", "127.0.0.1"]
        CLI().main()
        config = read_server_config()
        self.assertEqual(config["host"], "127.0.0.1")
        self.assertEqual(config["port"], DEFAULT_PORT)

    def test_invalid_configuration(self):
        """Test reading bad JSON on cli start."""
        write_server_config({})

        sys.argv = ["/bin/qpc", "server", "config", "--host", "127.0.0.1"]
        CLI().main()
        config = read_server_config()
        self.assertEqual(config["host"], "127.0.0.1")
        self.assertEqual(config["port"], DEFAULT_PORT)

    def test_run_command_no_config(self):
        """Test running command without config."""
        write_server_config({})

        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "cred"]
            CLI().main()
