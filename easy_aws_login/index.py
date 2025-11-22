"""Easy AWS Login - CLI tool for AWS console login via federation tokens."""

import argparse
import json
import sys
from getpass import getuser
from urllib.parse import quote_plus
from webbrowser import open_new_tab

import boto3
import requests
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from easy_aws_login.__version__ import __version__

# Constants
MAX_SESSION_NAME_LENGTH = 32
MIN_SESSION_DURATION_SECONDS = 900
AWS_FEDERATION_BASE_URL = "https://signin.aws.amazon.com/federation"
AWS_CONSOLE_URL = "https://console.aws.amazon.com/"
REQUEST_TIMEOUT_SECONDS = 10

# Optional import for clipboard functionality
try:
    import pyperclip
except ImportError:
    pyperclip = None  # type: ignore[assignment, misc]


class DurationTooShortError(Exception):
    """Raised when session duration is less than minimum required duration."""


def _get_aws_credentials(
    session: boto3.Session,
    profile_name: str,
    duration: int,
    issuer: str,
) -> dict:
    """Get AWS credentials using federation token or assume role.

    Args:
        session: Boto3 session object
        profile_name: AWS profile name
        duration: Session duration in seconds
        issuer: Issuer identifier for the session

    Returns:
        Dictionary containing AWS credentials (AccessKeyId, SecretAccessKey,
        SessionToken)

    Raises:
        ClientError: If AWS API calls fail

    """
    sts = session.client("sts")
    name = f"{getuser()}-{issuer}"
    if len(name) > MAX_SESSION_NAME_LENGTH:
        name = name[:MAX_SESSION_NAME_LENGTH]

    try:
        # Try to get federation token first (for IAM users)
        response = sts.get_federation_token(
            Name=name,
            DurationSeconds=duration,
            Policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [{"Action": "*", "Effect": "Allow", "Resource": "*"}],
                },
            ),
        )
    except ClientError:
        # If federation token fails, try assume role (for role-based profiles)
        # Note: boto3 doesn't provide a public API to get role_arn from profile config.
        # We access the internal profile_map as a workaround.
        # The `_profile_map` structure has been stable across boto3 versions
        # This is a workaround necessary until boto3 provides a public API for this use case.
        role_arn = session._session._profile_map[profile_name]["role_arn"]  # noqa: SLF001
        response = sts.assume_role(
            RoleSessionName=issuer,
            DurationSeconds=duration,
            RoleArn=role_arn,
        )

    return response["Credentials"]


def _create_signin_url(sign_in_token: str, issuer: str) -> str:
    """Create AWS console sign-in URL from federation token.

    Args:
        sign_in_token: AWS federation sign-in token
        issuer: Issuer identifier

    Returns:
        Complete sign-in URL for AWS console

    """
    destination = quote_plus(AWS_CONSOLE_URL)
    return (
        f"{AWS_FEDERATION_BASE_URL}?Action=login&Issuer={issuer}"
        f"&Destination={destination}&SigninToken={sign_in_token}"
    )


def _open_browser_or_fallback(sign_in_url: str, *, debug: bool) -> None:
    """Open browser with sign-in URL or provide fallback instructions.

    Args:
        sign_in_url: AWS console sign-in URL
        debug: Whether to show debug information

    """
    try:
        open_new_tab(sign_in_url)
    except OSError:
        print("Could not automatically open browser.")
        if debug:
            print(
                "WARNING: Debug mode enabled. The following URL contains "
                "sensitive credentials.",
                file=sys.stderr,
            )
            print(
                "This output is sent to stderr to reduce risk of logging. "
                "Use with caution.",
                file=sys.stderr,
            )
            print("Debug mode: Sign-in URL:", file=sys.stderr)
            print(sign_in_url, file=sys.stderr)
        else:
            print("For security reasons, the sign-in URL is not displayed.")
            print("Run with --debug flag to view the URL if needed.")
            if pyperclip:
                pyperclip.copy(sign_in_url)
                print("The sign-in URL has been copied to your clipboard.")
            else:
                print("Install pyperclip package to enable clipboard functionality:")
                print("pip install pyperclip")


def go(profile_name: str, duration: int, *, debug: bool = False) -> None:
    """Authenticate with AWS and open console login URL.

    Args:
        profile_name: AWS profile name to use
        duration: Session duration in seconds (minimum 900)
        debug: Enable debug mode to show sensitive information

    Raises:
        SystemExit: On configuration or network errors

    """
    try:
        session = boto3.session.Session(profile_name=profile_name)
    except (ProfileNotFound, NoCredentialsError) as e:
        print(f"Error: Unable to find AWS profile '{profile_name}'.")
        print("Please check your AWS configuration:")
        print("1. Verify the profile name in ~/.aws/config or ~/.aws/credentials")
        print("2. Ensure the profile is correctly configured")
        if debug:
            # Error details may contain sensitive info, send to stderr
            print(f"Detailed error: {e}", file=sys.stderr)
        sys.exit(1)

    issuer = f"{profile_name}-easy-aws-login"

    # Get AWS credentials
    try:
        credentials = _get_aws_credentials(session, profile_name, duration, issuer)
    except ClientError as e:
        error_msg = f"Failed to get AWS credentials: {e}"
        if debug:
            print(error_msg, file=sys.stderr)
        else:
            print("Failed to get AWS credentials.")
            print("Run with --debug flag for detailed error information.")
        sys.exit(1)

    # Create temporary credentials JSON
    json_temp_credentials = json.dumps(
        {
            "sessionId": credentials["AccessKeyId"],
            "sessionKey": credentials["SecretAccessKey"],
            "sessionToken": credentials["SessionToken"],
        },
    )

    # Get federation sign-in token
    quote_session = quote_plus(json_temp_credentials)
    get_token_url = (
        f"{AWS_FEDERATION_BASE_URL}?Action=getSigninToken&Session={quote_session}"
    )
    try:
        sign_in_token = requests.get(
            get_token_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ).json()["SigninToken"]
    except requests.exceptions.Timeout:
        print(
            "Request to AWS federation service timed out. "
            "Please check your network connection and try again.",
        )
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        # Error details may contain URLs or sensitive info, sanitize for non-debug
        if debug:
            print(
                f"Error connecting to AWS federation service: {e}",
                file=sys.stderr,
            )
        else:
            print("Error connecting to AWS federation service.")
            print("Run with --debug flag for detailed error information.")
        sys.exit(1)

    # Create sign-in URL and open browser
    sign_in_url = _create_signin_url(sign_in_token, issuer)
    _open_browser_or_fallback(sign_in_url, debug=debug)


def main() -> None:
    """Run the CLI application."""
    parser = argparse.ArgumentParser(description="Easy AWS Login")
    parser.add_argument(
        "profile",
        nargs="?",
        default="default",
        help="AWS profile name",
    )
    parser.add_argument(
        "duration",
        nargs="?",
        type=int,
        default=3600 * 12,
        help="Session duration in seconds",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (shows sensitive information)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

    args = parser.parse_args()

    if args.duration < MIN_SESSION_DURATION_SECONDS:
        error_message = (
            f"Duration must be at least {MIN_SESSION_DURATION_SECONDS} seconds"
        )
        raise DurationTooShortError(error_message)

    go(args.profile, args.duration, debug=args.debug)


if __name__ == "__main__":
    main()
