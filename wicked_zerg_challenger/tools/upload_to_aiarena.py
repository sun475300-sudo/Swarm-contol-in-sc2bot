#!/usr/bin/env python3
"""
AI Arena Auto-Uploader
=======================
Automatically upload bot to AI Arena using their API
"""

import requests
import json
from pathlib import Path
import sys
import os


class AIArenaUploader:
    """Upload bot to AI Arena"""

    def __init__(self):
        self.api_base = "https://aiarena.net/api"
        self.token = os.environ.get("AIARENA_TOKEN")
        self.bot_name = "WickedZergChallenger"

    def check_token(self):
        """Check if API token is set"""
        if not self.token:
            print("? AI Arena API token not found!\n")
            print("Please set your API token:")
            print("1. Go to https://aiarena.net/profile/token/")
            print("2. Copy your API token")
            print("3. Set environment variable:")
            print('   set AIARENA_TOKEN=your_token_here')
            print()
            return False

        print(f"? API token found: {self.token[:10]}...\n")
        return True

    def get_headers(self):
        """Get API headers"""
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

    def list_bots(self):
        """List user's bots"""
        print("? Fetching your bots...\n")

        try:
            response = requests.get(
                f"{self.api_base}/bots/",
                headers=self.get_headers()
            )
            response.raise_for_status()

            data = response.json()

            # Handle different response formats
            if isinstance(data, dict):
                bots = data.get('results', [])
            elif isinstance(data, list):
                bots = data
            else:
                print("? Unexpected API response format\n")
                return []

            if not bots:
                print("No bots found.\n")
                return []

            print(f"Found {len(bots)} bot(s):")
            for bot in bots:
                print(f"  - {bot['name']} (ID: {bot['id']}, Race: {bot['plays_race']})")
            print()

            return bots

        except requests.exceptions.RequestException as e:
            print(f"? Failed to fetch bots: {e}\n")
            return []

    def find_bot_by_name(self, name):
        """Find bot by name"""
        bots = self.list_bots()
        for bot in bots:
            if bot['name'] == name:
                return bot
        return None

    def create_bot(self):
        """Create new bot"""
        print(f"? Creating bot: {self.bot_name}...\n")

        bot_data = {
            "name": self.bot_name,
            "race": "Z",  # Zerg
            "bot_type": "python",
            "plays_race": "Z"
        }

        try:
            response = requests.post(
                f"{self.api_base}/bots/",
                headers=self.get_headers(),
                json=bot_data
            )
            response.raise_for_status()

            bot = response.json()
            print(f"? Bot created: {bot['name']} (ID: {bot['id']})\n")
            return bot

        except requests.exceptions.RequestException as e:
            print(f"? Failed to create bot: {e}\n")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}\n")
            return None

    def upload_bot_zip(self, bot_id, zip_path):
        """Upload bot ZIP file"""
        print(f"? Uploading bot package...\n")

        if not Path(zip_path).exists():
            print(f"? File not found: {zip_path}\n")
            return False

        try:
            with open(zip_path, 'rb') as f:
                files = {'bot_zip': f}
                headers = {"Authorization": f"Token {self.token}"}

                response = requests.post(
                    f"{self.api_base}/bots/{bot_id}/upload/",
                    headers=headers,
                    files=files
                )
                response.raise_for_status()

            print("? Bot uploaded successfully!\n")
            return True

        except requests.exceptions.RequestException as e:
            print(f"? Upload failed: {e}\n")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}\n")
            return False

    def upload(self, zip_path):
        """Complete upload process"""
        print("="*70)
        print("AI Arena Auto-Uploader")
        print("="*70)
        print()

        # Step 1: Check token
        if not self.check_token():
            return False

        # Step 2: Check if bot exists
        bot = self.find_bot_by_name(self.bot_name)

        if bot:
            print(f"??  Bot '{self.bot_name}' already exists (ID: {bot['id']})")
            print("This will update the existing bot.\n")
        else:
            # Step 3: Create bot
            bot = self.create_bot()
            if not bot:
                return False

        # Step 4: Upload ZIP
        if not self.upload_bot_zip(bot['id'], zip_path):
            return False

        print("="*70)
        print("? Upload Complete!")
        print("="*70)
        print()
        print(f"? Bot: {self.bot_name}")
        print(f"? View: https://aiarena.net/bots/{bot['id']}/")
        print()
        print("Next steps:")
        print("1. Verify bot details on AI Arena")
        print("2. Activate bot for competitions")
        print("3. Watch your bot compete!")
        print()

        return True


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python upload_to_aiarena.py <zip_file>")
        print()
        print("Example:")
        print("  python upload_to_aiarena.py WickedZergChallenger_20260110_120000.zip")
        print()
        sys.exit(1)

    zip_path = sys.argv[1]

    uploader = AIArenaUploader()

    try:
        success = uploader.upload(zip_path)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n? Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n? Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
