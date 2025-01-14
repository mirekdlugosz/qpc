"""Utilities for the source module."""

from argparse import ArgumentTypeError


def validate_port(arg):
    """Check that arg is a valid port.

    :param arg: either a string or an integer.
    :returns: The arg, as an integer.
    :raises: ValueError, if arg is not a valid port.
    """
    if isinstance(arg, str):
        try:
            arg = int(arg)
        except ValueError as exception:
            raise ArgumentTypeError(
                f"Port value {arg}"
                " should be a positive integer"
                " in the valid range (0-65535)"
            ) from exception
    elif not isinstance(arg, int):
        raise ArgumentTypeError(
            f"Port value {arg} should be a positive integer"
            " in the valid range (0-65535)"
        )

    # We need to support both system and user ports (see
    # https://en.wikipedia.org/wiki/Registered_port) because we don't
    # know how the user will have configured their system.
    if arg < 0 or arg > 65535:
        raise ArgumentTypeError(
            f"Port value {arg} should be a positive integer"
            " in the valid range (0-65535)"
        )

    return arg


# pylint: disable=R0912
def build_source_payload(args, add_none=True):
    """Construct payload from command line arguments.

    :param args: the command line arguments
    :param add_none: add None for a key if True vs. not in dictionary
    :returns: the dictionary for the request payload
    """
    req_payload = {"name": args.name}

    # Add necessary source parameters
    if hasattr(args, "type") and args.type:
        req_payload["source_type"] = args.type
    if hasattr(args, "hosts") and args.hosts:
        req_payload["hosts"] = args.hosts
    if hasattr(args, "exclude_hosts") and args.exclude_hosts:
        req_payload["exclude_hosts"] = args.exclude_hosts
    if hasattr(args, "credentials") and args.credentials:
        req_payload["credentials"] = args.credentials
    if hasattr(args, "port") and args.port:
        req_payload["port"] = args.port
    elif add_none:
        req_payload["port"] = None

    # Add source options
    options = None
    if hasattr(args, "ssl_cert_verify") and args.ssl_cert_verify is not None:
        ssl_cert_verify = args.ssl_cert_verify == "true"
        options = {"ssl_cert_verify": ssl_cert_verify}
    if hasattr(args, "disable_ssl") and args.disable_ssl is not None:
        disable_ssl = args.disable_ssl == "true"
        if options is None:
            options = {"disable_ssl": disable_ssl}
        else:
            options["disable_ssl"] = disable_ssl
    if hasattr(args, "ssl_protocol") and args.ssl_protocol is not None:
        if options is None:
            options = {"ssl_protocol": args.ssl_protocol}
        else:
            options["ssl_protocol"] = args.ssl_protocol
    if hasattr(args, "use_paramiko") and args.use_paramiko is not None:
        if options is None:
            options = {"use_paramiko": args.use_paramiko}
        else:
            options["use_paramiko"] = args.use_paramiko

    if options is not None:
        req_payload["options"] = options

    return req_payload
