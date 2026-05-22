import requests
import json

def get_facebook_names_by_ids(uid_list, access_token):
    """
    Get Facebook user names by their UIDs using Facebook Graph API

    Args:
        uid_list (list): List of Facebook user IDs
        access_token (str): Facebook App access token
    """
    names = {}

    for uid in uid_list:
        try:
            # Using Facebook Graph API to get user info
            url = f"https://graph.facebook.com/{uid}"
            params = {
                'fields': 'name',
                'access_token': access_token
            }

            response = requests.get(url, params=params)
            data = response.json()

            if 'name' in data:
                names[uid] = data['name']
                print(f"UID {uid}: {data['name']}")
            else:
                names[uid] = "Unknown"
                print(f"UID {uid}: Not found or private")

        except Exception as e:
            print(f"Error fetching name for UID {uid}: {e}")
            names[uid] = "Error"

    return names

# Example usage with your UIDs
uids = [
    "61555378641961",
    "61554840255034",
    "61554577945271",
    "61554888192197",
    "61554225371217",
    "61555326354208",
    "61551503611406",
    "61554385082741",
    "61554946388836",
    "61554939879123",
    "61555269236772",
    "61555207049044",
    "61554946838614",
    "61555400514826",
    "61555034884185",
    "61554782346513",
    "61554778487508",
    "61554354277294",
    "61555495317516",
    "61554781306924",
    "61555176161021",
    "61553632704348",
    "61554994787837",
    "61552958370141",
    "61555018265382",
    "61555159745525",
    "61555029125697",
    "61555092663867"
]

# You'll need to get a Facebook App access token from https://developers.facebook.com/tools/accesstoken/
# For testing purposes, you can use the App token tool to generate a token
access_token = "YOUR_FACEBOOK_APP_ACCESS_TOKEN"

names = get_facebook_names_by_ids(uids, access_token)
print("Facebook names lookup results:")
for uid, name in names.items():
    print(f"{uid}: {name}")