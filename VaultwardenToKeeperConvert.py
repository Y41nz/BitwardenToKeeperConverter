"""
Bitwarden to Keeper Conversion Script

Modified by: [Y41nz]
Date: [05.11.2024]
Original Author: Nam Namir
Licensed under the Apache License, Version 2.0
You may not use this file except in compliance with the License.
You may obtain a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS
OF ANY KIND, either express or implied. See the License for the specific language
governing permissions and limitations under the License.
"""

from datetime import datetime
import json
import os.path

# Bitwarden file path (organization only)
bitwarden_file_organization = r'###'  # Modified: Only organization Bitwarden file is used. Original code used separate normal and organization files.

# Output path of the Keeper file
keeper_file = r'###'  # Modified: Keeper output file path is different from the original.

# A flag to write the password change history into the note section
password_history_log = False

bitwarden_keeper_types = {
    # Numbers are for Bitwarden
    # Texts are for Keeper
    1: 'login',
    2: 'encryptedNotes',
    3: 'bankCard'
}

# Prompt user for the folder name to be exported
folder_name_to_export = input("Enter the folder name to be exported with all subcollections: ")  # Added: Prompt the user for folder name to filter export.

# Some variables to store data in
keeper = {
    'shared_folders': [],
    'records': []
}
bitwarden_folders = {}
bitwarden_collenctions = {}
bitwarden_org = {
    'items': []
}
counter = 0    # Count all items
counter_1 = 0  # Count items with type 1
counter_2 = 0  # Count items with type 2
counter_3 = 0  # Count items with type 3

# Open the Bitwarden JSON file (organization) and read items and collections
if os.path.isfile(bitwarden_file_organization):
    with open(bitwarden_file_organization, 'r', encoding='utf8') as bitwarden_org_json:
        bitwarden_org = json.load(bitwarden_org_json)
        bitwarden_items = bitwarden_org['items']
        # Convert Bitwarden collections in a format that can be used more easily during the conversion
        for collection in bitwarden_org['collections']:
            bitwarden_collenctions[collection['id']] = collection['name']
else:
    print(f"The file '{bitwarden_file_organization}' doesn't exist. Check it and try again.")
    exit(1)  # Modified: Exits script if organization file is not found, since no other input file is used.

# Function to determine if a collection is part of the specified folder or its subcollections
def is_in_target_folder(collection_name, target_folder_name):
    return collection_name.startswith(target_folder_name)  # Added: Helper function to filter based on folder name.

# Iterate over the items in bitwarden
for bitwarden_item in bitwarden_items:
    # Ensure all collectionIds are included in the filtering process
    if 'collectionIds' in bitwarden_item:
        collection_names = [bitwarden_collenctions.get(cid, '') for cid in bitwarden_item['collectionIds']]
        # If any of the collections match the target folder or its subcollections, include the item
        if not any(is_in_target_folder(collection_name, folder_name_to_export) for collection_name in collection_names):
            continue  # Modified: Filter items to export only those within the specified folder and its subcollections.

    # If the Bitwarden item is a login
    if bitwarden_item['type'] == 1:
        # Get URIs/URLs from Bitwarden item
        url_1 = None
        urls = {}
        if 'uris' in bitwarden_item['login']:
            for i in range(0, len(bitwarden_item['login']['uris'])):
                if i == 0:
                    url_1 = bitwarden_item['login']['uris'][0]['uri']
                elif i >= 1:
                    urls[f'$url::{i+1}'] = bitwarden_item['login']['uris'][i]['uri']

        # Form the base JSON format of a login in Keeper
        keeper_item = {
            'title': bitwarden_item['name'].strip(),
            'notes': bitwarden_item['notes'].replace('\u0010', '') if bitwarden_item['notes'] else '',
            '$type': 'login',
            'schema': [
                '$passkey::1',
                '$login::1',
                '$password::1',
                "$fileRef::1",
                '$url::1'
            ],
            'custom_fields': {},
            'login': bitwarden_item['login']['username'],
            'password': bitwarden_item['login']['password'],
            'login_url': url_1,
            'folders': []
        }

        # Add additional URLs to Keeper
        if urls:
            keeper_item['custom_fields'].update(urls)

        # If TOPT (MFA) is set in Bitwarden, add it to Keeper
        if bitwarden_item['login']['totp']:
            keeper_item['custom_fields'].update(
                {
                    '$oneTimeCode::1': bitwarden_item['login']['totp']
                }
            )
            keeper_item['schema'].append('$oneTimeCode::1')

        # Keep a record of password changes
        if bitwarden_item['passwordHistory'] and password_history_log:
            keeper_item['notes'] += '\n----- Password History -----\n'
            for password in bitwarden_item['passwordHistory']:
                keeper_item['notes'] += f"{str(password['password'])}  --  {str(password['lastUsedDate'])}\n"

        # Count the number of items with the type 1
        counter_1 += 1

    # If the Bitwarden item is a secure note
    if bitwarden_item['type'] == 2:
        # Convert the UTC (Bitwarden) to Epoch (Keeper)
        utc_creation_date = datetime.strptime(bitwarden_item['creationDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
        epoch_creation_date = (utc_creation_date - datetime(1970, 1, 1)).total_seconds()
        epoch_creation_date = int(str(int(epoch_creation_date)).ljust(13, '0'))

        # Form the base JSON format of a secure note in Keeper
        keeper_item = {
            'title': bitwarden_item['name'].strip(),
            'notes': None,
            '$type': 'encryptedNotes',
            'schema': [
                '$note::1',
                '$date::1',
            ],
            'custom_fields': {
                '$note::1': bitwarden_item['notes'].replace('\u0010', '') if bitwarden_item['notes'] else '',
                '$date::1': epoch_creation_date
            },
            'folders': []
        }

        # Count the number of items with the type 2
        counter_2 += 1

    # If the Bitwarden item is a card
    if bitwarden_item['type'] == 3:
        # Form the base JSON format of cards in Keeper
        keeper_item = {
            'title': bitwarden_item['name'].strip(),
            'notes': bitwarden_item['notes'].replace('\u0010', '') if bitwarden_item['notes'] else '',
            '$type': 'bankCard',
            'schema': [
                '$paymentCard::1',
                '$text:cardholderName:1',
                '$addressRef::1',
                "$fileRef::1",
            ],
            'custom_fields': {
                '$paymentCard::1': {
                    'cardNumber': bitwarden_item['card']['number'],
                    'cardExpirationDate': f"{str(bitwarden_item['card']['expMonth']).zfill(2)}/{bitwarden_item['card']['expYear']}",
                    'cardSecurityCode': bitwarden_item['card']['code']
                },
                '$text:cardholderName:1': bitwarden_item['card']['cardholderName'].strip() if bitwarden_item['card']['cardholderName'] else None,
                '$pinCode::1': None
            },
            'folders': []
        }

        # Count the number of items with the type 3
        counter_3 += 1

    # Add folders to Keeper
    if bitwarden_item['folderId']:
        keeper_item['folders'].append(
            {
                'folder': bitwarden_folders[bitwarden_item['folderId']].replace('/', '\\')
            }
        )

    # Add shared folders (collections) to Keeper
    if bitwarden_item['collectionIds']:
        for id in bitwarden_item['collectionIds']:
            keeper_item['folders'].append(
                {
                    'shared_folder': bitwarden_collenctions[id].replace('/', '\\'),
                    'can_edit': False,  # For security reasons
                    'can_share': False  # For security reasons
                }
            )

    # Add the newly formed Keeper item into a dictionary
    keeper['records'].append(keeper_item)

    # Count the number of items
    counter += 1

    print(f"{counter:>5}/{len(bitwarden_items)}  ::  Item {keeper_item['title']}")

# Convert and write Keeper JSON object to file
with open(keeper_file, 'w', encoding='utf8') as outfile:
    json.dump(keeper, outfile, ensure_ascii=False, indent=4)

# Print the stats
print(f"""
 [+]┏ {counter} items are saved in the file {keeper_file}.
    ┣━━━ Logins       : {counter_1}
    ┣━━━ Secure Notes : {counter_2}
    ┣━━━ Cards        : {counter_3}
    ┗━━━ Shared Items : {len(bitwarden_org['items'])} of {counter}
""")
