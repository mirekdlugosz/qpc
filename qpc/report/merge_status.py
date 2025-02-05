"""ReportMergeStatusCommand is used to show job merge information."""

import sys
from logging import getLogger

from requests import codes

from qpc import messages, report
from qpc.clicommand import CliCommand
from qpc.release import PKG_NAME
from qpc.request import GET
from qpc.translation import _

logger = getLogger(__name__)


# pylint: disable=too-few-public-methods
class ReportMergeStatusCommand(CliCommand):
    """Defines the job command.

    This command is for checking the job status of a merge command.
    """

    SUBCOMMAND = report.SUBCOMMAND
    ACTION = report.MERGE_STATUS

    def __init__(self, subparsers):
        """Create command."""
        # pylint: disable=no-member
        CliCommand.__init__(
            self,
            self.SUBCOMMAND,
            self.ACTION,
            subparsers.add_parser(self.ACTION),
            GET,
            report.ASYNC_MERGE_URI,
            [codes.ok],
        )
        self.parser.add_argument(
            "--job",
            dest="job_id",
            metavar="JOB_ID",
            help=_(messages.REPORT_JOB_ID_HELP),
            required=True,
        )

    def _build_req_params(self):
        self.req_path = report.ASYNC_MERGE_URI + str(self.args.job_id) + "/"

    def _handle_response_success(self):
        json_data = self.response.json()
        logger.info(
            _(messages.MERGE_JOB_ID_STATUS),
            {"job_id": self.args.job_id, "status": json_data.get("status").lower()}
        )
        if json_data.get("report_id"):
            logger.info(
                _(messages.DISPLAY_REPORT_ID),
                {
                    "report_id": json_data.get("report_id"),
                    "pkg_name": PKG_NAME,
                }
            )

    def _handle_response_error(self):  # pylint: disable=arguments-differ
        logger.error(_(messages.MERGE_JOB_ID_NOT_FOUND), self.args.job_id)
        sys.exit(1)
