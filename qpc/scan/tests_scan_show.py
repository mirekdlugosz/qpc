"""Test the CLI module."""

import sys
import unittest
from argparse import ArgumentParser, Namespace
from io import StringIO

import requests
import requests_mock

from qpc.request import CONNECTION_ERROR_MSG
from qpc.scan import SCAN_URI
from qpc.scan.show import ScanShowCommand
from qpc.tests_utilities import DEFAULT_CONFIG, HushUpStderr, redirect_stdout
from qpc.utils import get_server_location, write_server_config

PARSER = ArgumentParser()
SUBPARSER = PARSER.add_subparsers(dest="subcommand")


class ScanShowCliTests(unittest.TestCase):
    """Class for testing the scan show commands for qpc."""

    def setUp(self):
        """Create test setup."""
        write_server_config(DEFAULT_CONFIG)
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        sys.stderr = HushUpStderr()

    def tearDown(self):
        """Remove test setup."""
        # Restore stderr
        sys.stderr = self.orig_stderr

    def test_show_scan_ssl_err(self):
        """Testing the show scan command with a connection error."""
        scan_out = StringIO()
        url = get_server_location() + SCAN_URI + "?name=scan1"
        with requests_mock.Mocker() as mocker:
            mocker.get(url, exc=requests.exceptions.SSLError)
            nsc = ScanShowCommand(SUBPARSER)
            args = Namespace(name="scan1")
            with self.assertRaises(SystemExit):
                with redirect_stdout(scan_out):
                    nsc.main(args)
                    self.assertEqual(scan_out.getvalue(), CONNECTION_ERROR_MSG)

    def test_show_scan_conn_err(self):
        """Testing the show scan command with a connection error."""
        scan_out = StringIO()
        url = get_server_location() + SCAN_URI + "?name=scan1"
        with requests_mock.Mocker() as mocker:
            mocker.get(url, exc=requests.exceptions.ConnectTimeout)
            nsc = ScanShowCommand(SUBPARSER)
            args = Namespace(name="scan1")
            with self.assertRaises(SystemExit):
                with redirect_stdout(scan_out):
                    nsc.main(args)
                    self.assertEqual(scan_out.getvalue(), CONNECTION_ERROR_MSG)

    def test_show_scan_internal_err(self):
        """Testing the show scan command with an internal error."""
        scan_out = StringIO()
        url = get_server_location() + SCAN_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(url, status_code=500, json={"error": ["Server Error"]})
            nsc = ScanShowCommand(SUBPARSER)
            args = Namespace(name="scan1")
            with self.assertRaises(SystemExit):
                with redirect_stdout(scan_out):
                    nsc.main(args)
                    self.assertEqual(scan_out.getvalue(), "Server Error")

    # pylint: disable=invalid-name
    def test_show_scan_data_multiple_scans(self):
        """Testing the show scan command successfully with stubbed data."""
        scan_out = StringIO()
        url = get_server_location() + SCAN_URI
        get_url = get_server_location() + SCAN_URI + "1/"
        scan_entry = {"id": 1, "name": "scan1", "sources": ["source1"]}
        scan_entry2 = {"id": 2, "name": "scan2", "sources": ["source2"]}
        results = [scan_entry, scan_entry2]
        data = {"count": 2, "results": results}
        with requests_mock.Mocker() as mocker:
            mocker.get(url, status_code=200, json=data)
            mocker.get(get_url, status_code=200, json=scan_entry)
            nsc = ScanShowCommand(SUBPARSER)
            args = Namespace(name="scan1")
            with redirect_stdout(scan_out):
                nsc.main(args)
                expected = '{"id":1,"name":"scan1","sources":["source1"]}'
                self.assertEqual(
                    scan_out.getvalue().replace("\n", "").replace(" ", "").strip(),
                    expected,
                )

    def test_show_scan_data_one_scan(self):
        """Testing the show scan command successfully with stubbed data."""
        scan_out = StringIO()
        url = get_server_location() + SCAN_URI
        get_url = get_server_location() + SCAN_URI + "1/"
        scan_entry = {"id": 1, "name": "scan1", "sources": ["source1"]}
        results = [scan_entry]
        data = {"count": 1, "results": results}
        with requests_mock.Mocker() as mocker:
            mocker.get(url, status_code=200, json=data)
            mocker.get(get_url, status_code=200, json=scan_entry)
            nsc = ScanShowCommand(SUBPARSER)
            args = Namespace(name="scan1")
            with redirect_stdout(scan_out):
                nsc.main(args)
                expected = '{"id":1,"name":"scan1","sources":["source1"]}'
                self.assertEqual(
                    scan_out.getvalue().replace("\n", "").replace(" ", "").strip(),
                    expected,
                )
