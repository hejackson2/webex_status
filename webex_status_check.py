import argparse
import datetime
import os
import platform
import subprocess
import sys
import time

import requests


WEBEX_API_BASE = "https://webexapis.com/v1"
CHECK_INTERVAL_SECONDS = 30


def get_webex_person_status(email, token):
    url = f"{WEBEX_API_BASE}/people"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "email": email,
    }

    response = requests.get(url, headers=headers, params=params, timeout=15)

    if response.status_code == 401:
        raise RuntimeError("Unauthorized. Check your Webex access token.")

    if response.status_code == 403:
        raise RuntimeError(
            "Forbidden. Your token may not have permission to read this user's status."
        )

    if response.status_code >= 400:
        raise RuntimeError(f"Webex API error {response.status_code}: {response.text}")

    data = response.json()
    people = data.get("items", [])

    if not people:
        raise RuntimeError(f"No Webex user found for email: {email}")

    person = people[0]
    return person.get("status", "unknown")


def show_notification(title, message):
    system_name = platform.system().lower()

    if system_name == "darwin":
        show_macos_notification(title, message)
    elif system_name == "windows":
        show_windows_notification(title, message)
    else:
        print(f"\nNOTIFICATION: {title} - {message}\n")


def show_macos_notification(title, message):
    script = """
on run argv
    display notification (item 2 of argv) with title (item 1 of argv)
end run
"""

    subprocess.run(
        ["osascript", "-e", script, title, message],
        check=False,
    )


def show_windows_notification(title, message):
    safe_title = title.replace("'", "''")
    safe_message = message.replace("'", "''")

    powershell_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = '{safe_title}'
$notify.BalloonTipText = '{safe_message}'
$notify.Visible = $true
$notify.ShowBalloonTip(10000)

Start-Sleep -Seconds 10
$notify.Dispose()
"""

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            powershell_script,
        ],
        check=False,
    )


def speak_message(message):
    system_name = platform.system().lower()

    if system_name == "darwin":
        speak_macos(message)
    elif system_name == "windows":
        speak_windows(message)
    else:
        print(f"SOUND MESSAGE: {message}")


def speak_macos(message):
    subprocess.run(
        ["say", message],
        check=False,
    )


def speak_windows(message):
    safe_message = message.replace("'", "''")

    powershell_script = f"""
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Speak('{safe_message}')
"""

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            powershell_script,
        ],
        check=False,
    )


def watch_status(email, token):
    print(f"Watching Webex status for: {email}")
    print(f"Checking every {CHECK_INTERVAL_SECONDS} seconds.")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            status = get_webex_person_status(email, token)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"[{now}] {email} status: {status}")

            if status.lower() == "active":
                message = f"{email} has become active on Webex."

                show_notification("Webex User Active", message)
                speak_message(message)

                print("\nUser is active. Exiting.")
                break

            time.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nStopped by user.")
            break

        except Exception as error:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] Error: {error}")
            print(f"Retrying in {CHECK_INTERVAL_SECONDS} seconds...\n")
            time.sleep(CHECK_INTERVAL_SECONDS)


def main():
    parser = argparse.ArgumentParser(
        description="Repeatedly check the Webex status of a user by email."
    )

    parser.add_argument(
        "email",
        help="Email address of the Webex user to monitor.",
    )

    parser.add_argument(
        "--token",
        help="Webex access token. If omitted, WEBEX_ACCESS_TOKEN environment variable is used.",
    )

    args = parser.parse_args()

    token = args.token or os.getenv("WEBEX_ACCESS_TOKEN")

    if not token:
        print("Error: Webex access token is required.")
        print("Provide it with --token or set WEBEX_ACCESS_TOKEN.")
        sys.exit(1)

    watch_status(args.email, token)


if __name__ == "__main__":
    main()
