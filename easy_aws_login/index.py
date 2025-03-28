import argparse
import json
import sys
from getpass import getuser
from urllib.parse import quote_plus
from webbrowser import open_new_tab

import boto3
import requests
from botocore.exceptions import NoCredentialsError, ProfileNotFound


def go(profile_name, duration, debug=False):
    try:
        session = boto3.session.Session(profile_name=profile_name)
    except (ProfileNotFound, NoCredentialsError) as e:
        print(f"Error: Unable to find AWS profile '{profile_name}'.")
        print("Please check your AWS configuration:")
        print("1. Verify the profile name in ~/.aws/config or ~/.aws/credentials")
        print("2. Ensure the profile is correctly configured")
        if debug:
            print(f"Detailed error: {e}")
        sys.exit(1)

    sts = session.client("sts")
    issuer = f"{profile_name}-easy-aws-login"
    try:
        name = f"{getuser()}-{issuer}"
        if len(name) > 32:
            name = name[:32]
        response = sts.get_federation_token(
            Name=name,
            DurationSeconds=duration,
            Policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [{"Action": "*", "Effect": "Allow", "Resource": "*"}],
                }
            ),
        )
    except Exception:
        role_arn = session._session._profile_map[profile_name]["role_arn"]
        response = sts.assume_role(
            RoleSessionName=issuer, DurationSeconds=duration, RoleArn=role_arn
        )
    json_temp_credentials = json.dumps(
        {
            "sessionId": response["Credentials"]["AccessKeyId"],
            "sessionKey": response["Credentials"]["SecretAccessKey"],
            "sessionToken": response["Credentials"]["SessionToken"],
        }
    )

    quote_session = quote_plus(json_temp_credentials)
    get_token_url = f"https://signin.aws.amazon.com/federation?Action=getSigninToken&Session={quote_session}"
    try:
        sign_in_token = requests.get(get_token_url, timeout=10).json()["SigninToken"]
    except requests.exceptions.Timeout:
        print(
            "Request to AWS federation service timed out. Please check your network connection and try again."
        )
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to AWS federation service: {e}")
        sys.exit(1)

    destination = quote_plus("https://console.aws.amazon.com/")
    sign_in_url = f"https://signin.aws.amazon.com/federation?Action=login&Issuer={issuer}&Destination={destination}&SigninToken={sign_in_token}"
    try:
        open_new_tab(sign_in_url)
    except Exception:
        print("Could not automatically open browser.")
        if debug:
            print("Debug mode: Sign-in URL:")
            print(sign_in_url)
        else:
            print("For security reasons, the sign-in URL is not displayed.")
            print("Run with --debug flag to view the URL if needed.")
            try:
                # Try to copy to clipboard if pyperclip is available
                import pyperclip

                pyperclip.copy(sign_in_url)
                print("The sign-in URL has been copied to your clipboard.")
            except ImportError:
                print("Install pyperclip package to enable clipboard functionality:")
                print("pip install pyperclip")


def main():
    parser = argparse.ArgumentParser(description="Easy AWS Login")
    parser.add_argument(
        "profile", nargs="?", default="default", help="AWS profile name"
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

    args = parser.parse_args()

    if args.duration < 900:
        raise Exception("Duration must be at least 900 seconds")

    go(args.profile, args.duration, args.debug)


if __name__ == "__main__":
    main()
