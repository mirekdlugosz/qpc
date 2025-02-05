"""Test the CLI module."""

import json
import os
import sys
import time
import unittest
from argparse import ArgumentParser, Namespace  # noqa: I100
from io import StringIO  # noqa: I100
from unittest.mock import patch

import requests_mock

from qpc import messages
from qpc.cli import CLI
from qpc.report import REPORT_URI
from qpc.report.insights import ReportInsightsCommand
from qpc.scan import SCAN_JOB_URI
from qpc.tests_utilities import DEFAULT_CONFIG, HushUpStderr, redirect_stdout
from qpc.utils import create_tar_buffer, get_server_location, write_server_config

PARSER = ArgumentParser()
SUBPARSER = PARSER.add_subparsers(dest="subcommand")
VERSION = "0.9.4"


class ReportInsightsTests(unittest.TestCase):
    """Class for testing the insights report command."""

    # pylint: disable=invalid-name
    def setUp(self):
        """Create test setup."""
        write_server_config(DEFAULT_CONFIG)
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        self.test_tar_gz_filename = f"test_{time.time():.0f}.tar.gz"
        self.test_json_filename = f"test_{time.time():.0f}.json"
        sys.stderr = HushUpStderr()

    def tearDown(self):
        """Remove test setup."""
        # Restore stderr
        sys.stderr = self.orig_stderr
        try:
            os.remove(self.test_tar_gz_filename)
        except FileNotFoundError:
            pass

    def test_insights_report_as_json(self):
        """Testing retrieving insights report as json."""
        get_scanjob_url = get_server_location() + SCAN_JOB_URI + "1"
        get_scanjob_json_data = {"id": 1, "report_id": 1}
        get_report_url = get_server_location() + REPORT_URI + "1/insights/"
        get_report_json_data = {
            "id": 1,
            "report_id": 1,
            "hosts": {"00968d16-78b7-4bda-ab7d-668f3c0ef1ee": {"key": "value"}},
        }
        test_dict = {self.test_tar_gz_filename: get_report_json_data}
        buffer_content = create_tar_buffer(test_dict)
        with requests_mock.Mocker() as mocker:
            mocker.get(get_scanjob_url, status_code=200, json=get_scanjob_json_data)
            mocker.get(
                get_report_url,
                status_code=200,
                headers={"X-Server-Version": VERSION},
                content=buffer_content,
            )
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(
                scan_job_id="1", report_id=None, path=self.test_tar_gz_filename
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                self.assertIn(messages.REPORT_SUCCESSFULLY_WRITTEN, log.output[-1])

    def test_insights_report_as_json_report_id(self):
        """Testing retreiving insights report as json with report id."""
        get_report_url = get_server_location() + REPORT_URI + "1/insights/"
        get_report_json_data = {
            "id": 1,
            "report_id": 1,
            "hosts": {"00968d16-78b7-4bda-ab7d-668f3c0ef1ee": {"key": "value"}},
        }
        test_dict = {self.test_tar_gz_filename: get_report_json_data}
        buffer_content = create_tar_buffer(test_dict)
        with requests_mock.Mocker() as mocker:
            mocker.get(
                get_report_url,
                status_code=200,
                headers={"X-Server-Version": VERSION},
                content=buffer_content,
            )
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(
                scan_job_id=None, report_id="1", path=self.test_tar_gz_filename
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                self.assertIn(messages.REPORT_SUCCESSFULLY_WRITTEN, log.output[-1])

    # Test validation
    def test_insights_report_output_directory(self):
        """Testing fail because output directory."""
        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "report", "insights", "--output-file", "/"]
            CLI().main()

    def test_insights_report_output_directory_not_exist(self):
        """Testing fail because output directory does not exist."""
        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "report", "insights", "--output-file", "/foo/bar/"]
            CLI().main()

    def test_insights_report_output_file_empty(self):
        """Testing fail because output file empty."""
        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "report", "insights", "--output-file", ""]
            CLI().main()

    def test_insights_report_scan_job_not_exist(self):
        """Deployments report with nonexistent scanjob."""
        report_out = StringIO()

        get_scanjob_url = get_server_location() + SCAN_JOB_URI + "1"
        get_scanjob_json_data = {"id": 1, "report_id": 1}
        with requests_mock.Mocker() as mocker:
            mocker.get(get_scanjob_url, status_code=400, json=get_scanjob_json_data)
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(
                scan_job_id="1", report_id=None, path=self.test_tar_gz_filename
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(report_out):
                    nac.main(args)
                    self.assertEqual(
                        report_out.getvalue(), messages.REPORT_SJ_DOES_NOT_EXIST
                    )

    def test_insights_report_invalid_scan_job(self):
        """Deployments report with scanjob but no report_id."""
        report_out = StringIO()

        get_scanjob_url = get_server_location() + SCAN_JOB_URI + "1"
        get_scanjob_json_data = {"id": 1}
        with requests_mock.Mocker() as mocker:
            mocker.get(get_scanjob_url, status_code=200, json=get_scanjob_json_data)
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(
                scan_job_id="1", report_id=None, path=self.test_tar_gz_filename
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(report_out):
                    nac.main(args)
                    self.assertEqual(
                        report_out.getvalue(),
                        messages.REPORT_NO_DEPLOYMENTS_REPORT_FOR_SJ,
                    )

    @patch("qpc.report.insights.write_file")
    def test_insights_file_fails_to_write(self, file):
        """Testing insights failure while writing to file."""
        file.side_effect = EnvironmentError()
        get_report_url = get_server_location() + REPORT_URI + "1/insights/"
        get_report_json_data = {"id": 1, "report": [{"key": "value"}]}
        test_dict = {self.test_tar_gz_filename: get_report_json_data}
        buffer_content = create_tar_buffer(test_dict)
        with requests_mock.Mocker() as mocker:
            mocker.get(
                get_report_url,
                status_code=200,
                headers={"X-Server-Version": VERSION},
                content=buffer_content,
            )
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(
                scan_job_id=None, report_id="1", path=self.test_tar_gz_filename
            )
            with self.assertLogs(level="ERROR") as log:
                with self.assertRaises(SystemExit):
                    nac.main(args)
                err_msg = messages.WRITE_FILE_ERROR % {
                    "path": self.test_tar_gz_filename, "error": ""
                }
                self.assertIn(err_msg, log.output[0])

    def test_insights_nonexistent_directory(self):
        """Testing error for nonexistent directory in output."""
        fake_dir = "/kevan/is/awesome/insights.tar.gz"
        get_report_url = get_server_location() + REPORT_URI + "1/insights/"
        get_report_json_data = {"id": 1, "report": [{"key": "value"}]}
        test_dict = {self.test_tar_gz_filename: get_report_json_data}
        buffer_content = create_tar_buffer(test_dict)
        with requests_mock.Mocker() as mocker:
            mocker.get(get_report_url, status_code=200, content=buffer_content)
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(scan_job_id=None, report_id="1", path=fake_dir)
            with self.assertLogs(level="ERROR") as log:
                with self.assertRaises(SystemExit):
                    nac.main(args)
                err_msg = (
                    messages.REPORT_DIRECTORY_DOES_NOT_EXIST % os.path.dirname(fake_dir)
                )
                self.assertIn(err_msg, log.output[0])

    def test_insights_tar_path(self):
        """Testing error for nonjson output path."""
        non_tar_file = "/Users/insights.json"
        get_report_url = get_server_location() + REPORT_URI + "1/insights/"
        get_report_json_data = {"id": 1, "report": [{"key": "value"}]}
        test_dict = {self.test_tar_gz_filename: get_report_json_data}
        buffer_content = create_tar_buffer(test_dict)
        with requests_mock.Mocker() as mocker:
            mocker.get(
                get_report_url,
                status_code=200,
                headers={"X-Server-Version": VERSION},
                content=buffer_content,
            )
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(scan_job_id=None, report_id="1", path=non_tar_file)
            with self.assertLogs(level="ERROR") as log:
                with self.assertRaises(SystemExit):
                    nac.main(args)
                err_msg = messages.OUTPUT_FILE_TYPE % "tar.gz"
                self.assertIn(err_msg, log.output[0])

    def test_insights_report_id_not_exist(self):
        """Test insights with nonexistent report id."""
        get_report_url = get_server_location() + REPORT_URI + "1/insights/"
        get_report_json_data = {"id": 1, "report": [{"key": "value"}]}
        test_dict = {self.test_tar_gz_filename: get_report_json_data}
        buffer_content = create_tar_buffer(test_dict)
        with requests_mock.Mocker() as mocker:
            mocker.get(
                get_report_url,
                status_code=400,
                headers={"X-Server-Version": VERSION},
                content=buffer_content,
            )
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(
                scan_job_id=None, report_id="1", path=self.test_tar_gz_filename
            )
            with self.assertLogs(level="ERROR") as log:
                with self.assertRaises(SystemExit):
                    nac.main(args)
                err_msg = messages.REPORT_NO_INSIGHTS_REPORT_FOR_REPORT_ID % 1
                self.assertIn(err_msg, log.output[0])

    def test_insights_report_error_scan_job(self):
        """Testing error with scan job id."""
        get_scanjob_url = get_server_location() + SCAN_JOB_URI + "1"
        get_scanjob_json_data = {"id": 1, "report_id": 1}
        get_report_url = get_server_location() + REPORT_URI + "1/insights/"
        get_report_json_data = {"id": 1, "report": [{"key": "value"}]}
        test_dict = {self.test_tar_gz_filename: get_report_json_data}
        buffer_content = create_tar_buffer(test_dict)
        with requests_mock.Mocker() as mocker:
            mocker.get(get_scanjob_url, status_code=200, json=get_scanjob_json_data)
            mocker.get(
                get_report_url,
                status_code=400,
                headers={"X-Server-Version": VERSION},
                content=buffer_content,
            )
            nac = ReportInsightsCommand(SUBPARSER)
            args = Namespace(
                scan_job_id="1", report_id=None, path=self.test_tar_gz_filename
            )
            with self.assertLogs(level="ERROR") as log:
                with self.assertRaises(SystemExit):
                    nac.main(args)
                err_msg = messages.REPORT_NO_INSIGHTS_REPORT_FOR_SJ % 1
                self.assertIn(err_msg, log.output[0])


def test_insights_report_as_json_no_output_file(caplog, capsys, requests_mock):
    """Testing retrieving insights report as json without output file."""
    caplog.set_level("INFO")
    report_url = get_server_location() + REPORT_URI + "1/insights/"
    report_json_data = {
        "id": 1,
        "report_id": 1,
        "hosts": {"00968d16-78b7-4bda-ab7d-668f3c0ef1ee": {"key": "value"}},
    }
    json_filename = f"test_{time.time():.0f}.json"
    expected_json = {json_filename: report_json_data}
    requests_mock.get(
        report_url,
        status_code=200,
        json=expected_json,
        headers={"X-Server-Version": VERSION},
    )
    sys.argv = [
        "/bin/qpc",
        "report",
        "insights",
        "--report",
        "1",
    ]
    CLI().main()
    captured = capsys.readouterr()
    assert caplog.messages[-1] == messages.REPORT_SUCCESSFULLY_WRITTEN
    assert json.loads(captured.out)
