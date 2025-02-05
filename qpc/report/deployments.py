"""ReportDeploymentsCommand is to show deployments report."""


import sys
from logging import getLogger

from requests import codes

from qpc import messages, report, scan
from qpc.clicommand import CliCommand
from qpc.request import GET, request
from qpc.translation import _
from qpc.utils import (
    check_extension,
    extract_json_from_tar,
    validate_write_file,
    write_file,
)

logger = getLogger(__name__)


# pylint: disable=too-few-public-methods
class ReportDeploymentsCommand(CliCommand):
    """Defines the report deployments command.

    This command is for showing the deployments report.
    """

    SUBCOMMAND = report.SUBCOMMAND
    ACTION = report.DEPLOYMENTS

    def __init__(self, subparsers):
        """Create command."""
        # pylint: disable=no-member
        CliCommand.__init__(
            self,
            self.SUBCOMMAND,
            self.ACTION,
            subparsers.add_parser(self.ACTION),
            GET,
            report.REPORT_URI,
            [codes.ok],
        )
        id_group = self.parser.add_mutually_exclusive_group(required=True)
        id_group.add_argument(
            "--scan-job",
            dest="scan_job_id",
            metavar="SCAN_JOB_ID",
            help=_(messages.REPORT_SCAN_JOB_ID_HELP),
        )
        id_group.add_argument(
            "--report",
            dest="report_id",
            metavar="REPORT_ID",
            help=_(messages.REPORT_REPORT_ID_HELP),
        )

        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--json",
            dest="output_json",
            action="store_true",
            help=_(messages.REPORT_OUTPUT_JSON_HELP),
        )
        group.add_argument(
            "--csv",
            dest="output_csv",
            action="store_true",
            help=_(messages.REPORT_OUTPUT_CSV_HELP),
        )

        self.parser.add_argument(
            "--output-file",
            dest="path",
            metavar="PATH",
            help=_(messages.REPORT_PATH_HELP),
        )
        self.parser.add_argument(
            "--mask",
            dest="mask",
            action="store_true",
            help=_(messages.REPORT_MASK_HELP),
            required=False,
        )
        self.report_id = None
        self.min_server_version = "0.9.2"

    def _validate_args(self):
        CliCommand._validate_args(self)
        extension = None
        if self.args.output_json:
            extension = ".json"
            self.req_headers = {"Accept": "application/json+gzip"}
        if self.args.output_csv:
            extension = ".csv"
            self.req_headers = {"Accept": "text/csv"}
        if self.args.mask:
            self.req_params = {"mask": True}
        if extension:
            check_extension(extension, self.args.path)

        try:
            if self.args.path is not None:
                validate_write_file(self.args.path, "output-file")
        except ValueError as error:
            logger.error(error)
            sys.exit(1)

        if self.args.report_id is None:
            # Lookup scan job id
            response = request(
                parser=self.parser,
                method=GET,
                path=f"{scan.SCAN_JOB_URI}{self.args.scan_job_id}",
                payload=None,
            )
            if response.status_code == codes.ok:  # pylint: disable=no-member
                json_data = response.json()
                self.report_id = json_data.get("report_id")
                if self.report_id:
                    self.req_path = (
                        f"{self.req_path}"
                        f"{self.report_id}"
                        f"{report.DEPLOYMENTS_PATH_SUFFIX}"
                    )
                else:
                    logger.error(
                        _(messages.REPORT_NO_DEPLOYMENTS_REPORT_FOR_SJ),
                        self.args.scan_job_id
                    )
                    sys.exit(1)
            else:
                logger.error(
                    _(messages.REPORT_SJ_DOES_NOT_EXIST),
                    self.args.scan_job_id
                )
                sys.exit(1)
        else:
            self.report_id = self.args.report_id
            self.req_path = (
                f"{self.req_path}{self.report_id}{report.DEPLOYMENTS_PATH_SUFFIX}"
            )

    def _handle_response_success(self):
        file_content = None
        if self.args.output_json:
            file_content = extract_json_from_tar(self.response.content)
        else:
            file_content = self.response.text

        try:
            write_file(self.args.path, file_content)
            logger.info(_(messages.REPORT_SUCCESSFULLY_WRITTEN))
        except EnvironmentError as err:
            logger.error(
                _(messages.WRITE_FILE_ERROR),
                {"path": self.args.path, "error": err}
            )
            sys.exit(1)

    def _handle_response_error(self):  # pylint: disable=arguments-differ
        if self.args.report_id is None:
            if self.response.status_code == 428:
                logger.error(
                    _(messages.REPORT_COULD_NOT_BE_MASKED_SJ), self.args.scan_job_id
                )
            else:
                logger.error(
                    _(messages.REPORT_NO_DEPLOYMENTS_REPORT_FOR_SJ),
                    self.args.scan_job_id
                )
        else:
            if self.response.status_code == 428:
                logger.error(
                    _(messages.REPORT_COULD_NOT_BE_MASKED_REPORT_ID),
                    self.args.report_id
                )
            else:
                logger.error(
                    _(messages.REPORT_NO_DEPLOYMENTS_REPORT_FOR_REPORT_ID),
                    self.args.report_id
                )
        sys.exit(1)
