import requests
import json

def LIKE_PAGE(
    self,
    page_id: str,
    doc_id: str = "25463905889878308"
):
    """
    Like / Follow Page Facebook
    """

    if not isinstance(page_id, str):
        return {"success": False, "error": "page_id must be string"}

    try:
        self.login()

        if not self.ready:
            return {"success": False, "error": "Not logged in"}

        variables = {
            "input": {
                "is_tracking_encrypted": False,
                "page_id": page_id,
                "source": None,
                "tracking": None,
                "actor_id": self.uid,
                "client_mutation_id": "1"
            },
            "scale": 1
        }

        payload = {
            "av": self.uid,
            "__user": self.uid,
            "fb_dtsg": self.fb_dtsg,
            "lsd": self.lsd,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "CometProfilePlusLikeMutation",
            "variables": json.dumps(variables),
            "server_timestamps": "true",
            "doc_id": doc_id
        }

        headers = self.header.copy()

        headers.update({
            "x-fb-friendly-name": "CometProfilePlusLikeMutation",
            "x-fb-lsd": self.lsd
        })

        response = requests.post(
            "https://www.facebook.com/api/graphql/",
            headers=headers,
            cookies=self.cookie_dict,
            data=payload
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}"
            }

        data = response.json()

        if "errors" in data:
            return {
                "success": False,
                "error": data["errors"][0].get("description")
            }

        return {
            "success": True,
            "page_id": page_id,
            "response": data
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
print(LIKE_PAGE())