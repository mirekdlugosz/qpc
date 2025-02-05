"""Test the CLI module."""

import json
import os
import sys
import time
import unittest
from argparse import ArgumentParser, Namespace
from io import StringIO

import requests_mock

from qpc import messages
from qpc.cli import CLI
from qpc.server import STATUS_URI
from qpc.server.status import ServerStatusCommand
from qpc.tests_utilities import DEFAULT_CONFIG, HushUpStderr, redirect_stdout
from qpc.utils import get_server_location, write_server_config

TMP_KEY = "/tmp/testkey"
PARSER = ArgumentParser()
SUBPARSER = PARSER.add_subparsers(dest="subcommand")


class ServerStatusTests(unittest.TestCase):
    """Class for testing the server status command for qpc."""

    # pylint: disable=invalid-name
    def setUp(self):
        """Create test setup."""
        write_server_config(DEFAULT_CONFIG)
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        self.test_json_filename = f"test_{time.time():.0f}.json"
        sys.stderr = HushUpStderr()

    def tearDown(self):
        """Remove test setup."""
        # Restore stderr
        sys.stderr = self.orig_stderr
        try:
            os.remove(self.test_json_filename)
        except FileNotFoundError:
            pass

    def test_download_server_status(self):
        """Testing recording server status command in a file."""
        get_status_url = get_server_location() + STATUS_URI
        get_status_json_data = {
            "api_version": 1,
            "build": "a64eee4",
            "environment_vars": {"key": "value"},
        }
        with requests_mock.Mocker() as mocker:
            mocker.get(get_status_url, status_code=200, json=get_status_json_data)
            ssc = ServerStatusCommand(SUBPARSER)
            args = Namespace(path=self.test_json_filename)
            with self.assertLogs(level="INFO") as log:
                ssc.main(args)
                expected_message = messages.STATUS_SUCCESSFULLY_WRITTEN
                self.assertIn(expected_message, log.output[-1])
            with open(self.test_json_filename, "r", encoding="utf-8") as json_file:
                data = json_file.read()
                file_content_dict = json.loads(data)
            self.assertDictEqual(get_status_json_data, file_content_dict)

    def test_print_server_status(self):
        """Testing recording server status command in a file."""
        status_out = StringIO()

        get_status_url = get_server_location() + STATUS_URI
        get_status_json_data = {
            "api_version": 1,
            "build": "a64eee4",
            "environment_vars": {"key": "value"},
        }
        with requests_mock.Mocker() as mocker:
            mocker.get(get_status_url, status_code=200, json=get_status_json_data)
            ssc = ServerStatusCommand(SUBPARSER)
            args = Namespace(path=None)
            with redirect_stdout(status_out):
                ssc.main(args)
                self.assertDictEqual(
                    json.loads(status_out.getvalue().strip()), get_status_json_data
                )

    def test_write_status_output_directory_not_exist(self):
        """Testing fail because output directory does not exist."""
        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "server", "status", "--output-file", "/foo/bar/"]
            CLI().main()

    def test_write_status_output_file_empty(self):
        """Testing fail because output file empty."""
        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "server", "status", "--output-file"]
            CLI().main()

    def test_status_unexpected_failure(self):
        """Testing getting status with unexpected failure."""
        status_out = StringIO()

        get_status_url = get_server_location() + STATUS_URI
        get_status_json_data = {"api": 1}
        with requests_mock.Mocker() as mocker:
            mocker.get(get_status_url, status_code=400, json=get_status_json_data)
            ssc = ServerStatusCommand(SUBPARSER)
            args = Namespace(path=None)
            with self.assertRaises(SystemExit):
                with redirect_stdout(status_out):
                    ssc.main(args)
                    self.assertEqual(
                        status_out.getvalue(), messages.SERVER_STATUS_FAILURE
                    )
