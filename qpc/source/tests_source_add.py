"""Test the CLI module."""

import os
import sys
import unittest
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from io import StringIO

import requests
import requests_mock

from qpc import messages
from qpc.cli import CLI
from qpc.cred import CREDENTIAL_URI
from qpc.request import CONNECTION_ERROR_MSG
from qpc.source import SOURCE_URI
from qpc.source.add import SourceAddCommand
from qpc.source.utils import validate_port
from qpc.tests_utilities import DEFAULT_CONFIG, HushUpStderr, redirect_stdout
from qpc.utils import get_server_location, write_server_config

TMP_HOSTFILE = "/tmp/testhostsfile"
PARSER = ArgumentParser()
SUBPARSER = PARSER.add_subparsers(dest="subcommand")


# pylint: disable=too-many-public-methods
class SourceAddCliTests(unittest.TestCase):
    """Class for testing the source add commands for qpc."""

    def setUp(self):
        """Create test setup."""
        write_server_config(DEFAULT_CONFIG)
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        sys.stderr = HushUpStderr()
        if os.path.isfile(TMP_HOSTFILE):
            os.remove(TMP_HOSTFILE)
        with open(TMP_HOSTFILE, "w", encoding="utf-8") as test_hostfile:
            test_hostfile.write("1.2.3.4\n")
            test_hostfile.write("1.2.3.[1:10]\n")

    def tearDown(self):
        """Remove test case setup."""
        # Restore stderr
        sys.stderr = self.orig_stderr
        if os.path.isfile(TMP_HOSTFILE):
            os.remove(TMP_HOSTFILE)

    def test_add_req_args_err(self):
        """Testing the add source command required flags."""
        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "source", "add", "--name", "source1"]
            CLI().main()

    def test_add_process_file(self):
        """Testing the add source command process file."""
        with self.assertRaises(SystemExit):
            sys.argv = [
                "/bin/qpc",
                "source",
                "add",
                "--name",
                "source1",
                "--type",
                "network",
                "--hosts",
                TMP_HOSTFILE,
                "--cred",
                "cred1",
            ]
            CLI().main()

    def test_validate_port_string(self):
        """Testing the add source command with port validation non-integer."""
        source_out = StringIO()
        with self.assertRaises(ArgumentTypeError):
            with redirect_stdout(source_out):
                validate_port("ff")
                self.assertTrue("Port value ff" in source_out.getvalue())

    def test_validate_port_bad_type(self):
        """Testing the add source command with port validation bad type."""
        source_out = StringIO()
        with self.assertRaises(ArgumentTypeError):
            with redirect_stdout(source_out):
                validate_port(["ff"])
                self.assertTrue("Port value ff" in source_out.getvalue())

    def test_validate_port_range_err(self):
        """Test the add source command with port validation out of range."""
        source_out = StringIO()
        with self.assertRaises(ArgumentTypeError):
            with redirect_stdout(source_out):
                validate_port("65537")
                self.assertTrue("Port value 65537" in source_out.getvalue())

    def test_validate_port_good(self):
        """Testing the add source command with port validation success."""
        val = validate_port("80")
        self.assertEqual(80, val)

    def test_add_source_name_dup(self):
        """Testing the add source command duplicate name."""
        source_out = StringIO()
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        error = {"name": ["source with this name already exists."]}
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=400, json=error)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source_dup",
                cred=["cred1"],
                type="network",
                hosts=["1.2.3.4"],
                port=22,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    nac.main(args)
                    nac.main(args)
                    self.assertTrue(
                        "source with this name already exists." in source_out.getvalue()
                    )

    def test_add_source_cred_less(self):
        """Testing the add source command with a some invalid cred."""
        source_out = StringIO()
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1%2Ccred2"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1", "cred2"],
                hosts=["1.2.3.4"],
                type="network",
                port=22,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    nac.main(args)
                    self.assertTrue(
                        "An error occurred while processing "
                        'the "--cred" input' in source_out.getvalue()
                    )

    def test_add_source_cred_err(self):
        """Testing the add source command with an cred err."""
        source_out = StringIO()
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1%2Ccred2"
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=500)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1", "cred2"],
                hosts=["1.2.3.4"],
                type="network",
                port=22,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    nac.main(args)
                    self.assertTrue(
                        "An error occurred while processing "
                        'the "--cred" input' in source_out.getvalue()
                    )

    def test_add_source_ssl_err(self):
        """Testing the add source command with a connection error."""
        source_out = StringIO()
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, exc=requests.exceptions.SSLError)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=["1.2.3.4"],
                type="network",
                port=22,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    nac.main(args)
                    self.assertEqual(source_out.getvalue(), CONNECTION_ERROR_MSG)

    def test_add_source_conn_err(self):
        """Testing the add source command with a connection error."""
        source_out = StringIO()
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, exc=requests.exceptions.ConnectTimeout)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=["1.2.3.4"],
                type="network",
                port=22,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    nac.main(args)
                    self.assertEqual(source_out.getvalue(), CONNECTION_ERROR_MSG)

    ##################################################
    # Network Source Test
    ##################################################
    def test_add_source_net_one_host(self):
        """Testing add network source command successfully with one host."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=["1.2.3.4"],
                type="network",
                port=22,
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])

    def test_add_source_net_valid_hosts(self):
        """Testing add network source command with hosts in valid formats."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=[
                    "10.10.181.9",
                    "10.10.181.8/16",
                    "10.10.128.[1:25]",
                    "10.10.[1:20].25",
                    "localhost",
                    "mycentos.com",
                    "my-rhel[a:d].company.com",
                    "my-rhel[120:400].company.com",
                ],
                type="network",
                port=22,
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])

    def test_add_source_with_paramiko(self):
        """Testing add network source command with use_paramiko set to true."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=["10.10.181.9"],
                use_paramiko=True,
                type="network",
                port=22,
            )

            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])

    def test_add_source_with_paramiko_and_ssl(self):
        """Testing add network source command with use_paramiko set to true."""
        # pylint: disable=invalid-name
        source_out = StringIO()
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=400)
            nac = SourceAddCommand(SUBPARSER)

            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=["10.10.181.9"],
                ssl_cert_verify="False",
                use_paramiko=True,
                type="network",
                port=22,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(source_out):
                    nac.main(args)

    def test_add_source_one_excludehost(self):
        """Testing the add network source command with one exclude host."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=["1.2.3.4"],
                type="network",
                exclude_hosts=["1.2.3.4"],
                port=22,
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])

    def test_add_source_exclude_hosts(self):
        """Testing add network source command with many valid exclude hosts."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=[
                    "10.10.181.9",
                    "10.10.181.8/16",
                    "10.10.128.[1:25]",
                    "10.10.[1:20].25",
                    "localhost",
                    "mycentos.com",
                    "my-rhel[a:d].company.com",
                    "my-rhel[120:400].company.com",
                ],
                exclude_hosts=[
                    "10.10.181.9",
                    "10.10.181.8/16",
                    "10.10.[1:20].25",
                    "localhost",
                    "my-rhel[a:d].company.com",
                ],
                type="network",
                port=22,
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])

    ##################################################
    # Vcenter Source Test
    ##################################################
    def test_add_source_vc(self):
        """Testing the add vcenter source command successfully."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1", cred=["cred1"], hosts=["1.2.3.4"], type="vcenter"
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])

    def test_add_source_with_ssl_params(self):
        """Testing add vcenter source command with all ssl params."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=["10.10.181.9"],
                ssl_cert_verify="True",
                disable_ssl="False",
                ssl_protocol="SSL_PROTOCOL_SSLv23",
                type="vcenter",
                port=22,
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])

    ##################################################
    # Satellite Source Test
    ##################################################
    def test_add_source_sat(self):
        """Testing the add satellite source command successfully."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1", cred=["cred1"], hosts=["1.2.3.4"], type="satellite"
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])

    def test_add_source_sat_no_ssl(self):
        """Testing the add satellite with ssl_cert_verify set to false."""
        get_cred_url = get_server_location() + CREDENTIAL_URI + "?name=cred1"
        cred_results = [{"id": 1, "name": "cred1"}]
        get_cred_data = {"count": 1, "results": cred_results}
        post_source_url = get_server_location() + SOURCE_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(get_cred_url, status_code=200, json=get_cred_data)
            mocker.post(post_source_url, status_code=201)
            nac = SourceAddCommand(SUBPARSER)
            args = Namespace(
                name="source1",
                cred=["cred1"],
                hosts=["1.2.3.4"],
                type="satellite",
                ssl_cert_verify="false",
            )
            with self.assertLogs(level="INFO") as log:
                nac.main(args)
                expected_message = messages.SOURCE_ADDED % "source1"
                self.assertIn(expected_message, log.output[-1])
