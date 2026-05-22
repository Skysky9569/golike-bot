"""
Facebook Web API Module
Refactor từ FB_WEB_API.py để tích hợp vào module golike_facebook
"""
import requests
import json
import time
import random
import mimetypes
import re
import base64
import uuid
from typing import Dict, Any, Optional

from golike_core.logging import logger


class CookieHandler:
    @staticmethod
    def to_dict(cookie_str: str) -> Dict[str, str]:
        return {k.strip(): v.strip() for item in cookie_str.split(";")
                if "=" in item for k, v in [item.split("=", 1)]}


class NumberEncoder:
    @staticmethod
    def to_base36(num: int) -> str:
        chars = "0123456789abcdefghijklmnopqrstuvwxyz"
        if num == 0:
            return "0"
        result = ""
        while num:
            num, remainder = divmod(num, 36)
            result = chars[remainder] + result
        return result


class HTMLExtractor:
    @staticmethod
    def find_pattern(html: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, html)
        return match.group(1) if match else None

    @staticmethod
    def extract_token(html: str) -> Optional[str]:
        patterns = [
            r'DTSGInitialData".*?"token":"([^"]+)"',
            r'"token":"([^"]+)"',
        ]
        for pattern in patterns:
            result = HTMLExtractor.find_pattern(html, pattern)
            if result:
                return result
        return None
    @staticmethod
    def extract_lsd(html: str) -> Optional[str]:
        patterns = [
            r'LSD".*?"token":"([^"]+)"',
            r'"lsd"\s*:\s*"([^"]+)"',
        ]
        for pattern in patterns:
            result = HTMLExtractor.find_pattern(html, pattern)
            if result:
                return result
        return None
    @staticmethod
    def extract_user_id(html: str) -> Optional[str]:
        patterns = [
            r'"actorID":"(\d+)"',
            r'"USER_ID":"(\d+)"',
            r'c_user=(\d+)',
        ]
        for pattern in patterns:
            result = HTMLExtractor.find_pattern(html, pattern)
            if result:
                return result
        return None

    @staticmethod
    def extract_revision(html: str) -> Optional[str]:
        pattern = r'client_revision["\s:]+(\d+)'
        return HTMLExtractor.find_pattern(html, pattern)

    @staticmethod
    def extract_jazoest(html: str) -> Optional[str]:
        pattern = r'jazoest=(\d+)'
        return HTMLExtractor.find_pattern(html, pattern)


class FacebookSession:
    def __init__(self, cookie: str):
        self.cookie = cookie
        self.token = None
        self.user_id = None
        self.revision = None
        self.jazoest = None
        self.lsd = None

    def authenticate(self) -> bool:
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "max-age=0",
            "cookie": self.cookie,
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(
                "https://www.facebook.com/",
                headers=headers,
                cookies=CookieHandler.to_dict(self.cookie),
                timeout=30
            )

            html = response.text
            self.token = HTMLExtractor.extract_token(html)
            self.user_id = HTMLExtractor.extract_user_id(html)
            self.revision = HTMLExtractor.extract_revision(html) or "1000000"
            self.jazoest = HTMLExtractor.extract_jazoest(html) or "0"
            self.lsd = HTMLExtractor.extract_lsd(html) or "0"
            
            # KHẨN CẤP: Kiểm tra có lấy được token/user_id không
            if not self.token or not self.user_id:
                logger.error("Không thể lấy token hoặc user_id từ Facebook response!")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Lỗi trong quá trình xác thực Facebook: {e}")
            return False


class GenData:
    def __init__(self, session: FacebookSession):
        self.session = session
        self.request_counter = 0

    def build_REACTION(self, reaction: str, ID_POST: str, doc_id='null') -> Dict[str, Any]:
        if doc_id == 'null':
            self.docid = '24198888476452283'
        else:
            self.docid = doc_id
        self.request_counter += 1
        reaction_id_list = [1635855486666999,1678524932434102,613557422527858,115940658764963,478547315650144,908563459236466,444813342392137,'ERR']
        reaction_id_ = reaction_id_list[0] if reaction == "LIKE" else reaction_id_list[1] if reaction == "LOVE" else reaction_id_list[2] if reaction == 'CARE' else reaction_id_list[3] if reaction == 'HAHA' else reaction_id_list[4] if reaction == 'WOW' else reaction_id_list[5] if reaction == 'SAD' else reaction_id_list[6] if reaction == 'ANGRY' else reaction_id_list[7]
        if reaction_id_ == "ERR":
            return {'err': 'Không Thể Sử Dụng Loại Cảm Xúc Này'}

        s = "feedback:" + str(ID_POST)
        self.idpost = base64.b64encode(s.encode("utf-8")).decode("utf-8")
        payload = {
            'av': self.session.user_id,
            '__user': self.session.user_id,
            '__req': NumberEncoder.to_base36(self.request_counter),
            '__rev': self.session.revision,
            'fb_dtsg': self.session.token,
            'jazoest': self.session.jazoest,
            'lsd': self.session.lsd,
            '__spin_r': self.session.revision,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'CometUFIFeedbackReactMutation',
            'server_timestamps': 'true',
            'variables': '{"input":{"attribution_id_v2":"CometHomeRoot.react,comet.home,via_cold_start,1765901136948,422377,4748854339,,","feedback_id":"'+self.idpost+'","feedback_reaction_id":"'+str(reaction_id_)+'","feedback_source":"NEWS_FEED","is_tracking_encrypted":true,"tracking":[],"session_id":"'+str(uuid.uuid4())+'","actor_id":"'+self.session.user_id+'","client_mutation_id":"1"},"useDefaultActor":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false}',
            'doc_id': self.docid,
        }
        return payload

    def build_CMT(self, cmt: str, ID_POST: str, Group_id: str, doc_id='null') -> Dict[str, Any]:
        if doc_id == 'null':
            self.docid = '24615176934823390'
        else:
            self.docid = doc_id
        s = "feedback:" + str(ID_POST)
        self.idpost = base64.b64encode(s.encode("utf-8")).decode("utf-8")
        payload = {
            'av': self.session.user_id,
            '__user': self.session.user_id,
            '__req': NumberEncoder.to_base36(self.request_counter),
            '__rev': self.session.revision,
            'fb_dtsg': self.session.token,
            'jazoest': self.session.jazoest,
            'lsd': self.session.lsd,
            '__spin_r': self.session.revision,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'CometUFIFeedbackReactMutation',
            'server_timestamps': 'true',
            'variables': '{"feedLocation":"DEDICATED_COMMENTING_SURFACE","feedbackSource":110,"groupID":'+Group_id+',"input":{"client_mutation_id":"3","actor_id":"'+self.session.user_id+'","attachments":null,"feedback_id":"'+self.idpost+'","formatting_style":null,"message":{"ranges":[],"text":"'+cmt+'"},"attribution_id_v2":"CometHomeRoot.react,comet.home,unexpected,1765906156209,334250,4748854339,,;CometPhotoRoot.react,comet.mediaviewer.photo,via_cold_start,1765906141242,783051,,82,","vod_video_timestamp":null,"is_tracking_encrypted":true,"tracking":[],"feedback_source":"DEDICATED_COMMENTING_SURFACE","idempotence_token":"client:'+str(uuid.uuid4())+'","session_id":"'+str(uuid.uuid4())+'"},"inviteShortLinkKey":null,"renderLocation":null,"scale":1,"useDefaultActor":false,"focusCommentID":null,"__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false}',
            'doc_id': self.docid,
        }
        return payload

    def build_Follow(self, USERID: str, doc_id='null'):
        if doc_id == 'null':
            self.docid = '32658454793801856'
        else:
            self.docid = doc_id
        payload = {
            'av': self.session.user_id,
            '__user': self.session.user_id,
            '__req': NumberEncoder.to_base36(self.request_counter),
            '__rev': self.session.revision,
            'fb_dtsg': self.session.token,
            'jazoest': self.session.jazoest,
            'lsd': self.session.lsd,
            '__spin_r': self.session.revision,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'CometUserFollowMutation',
            'server_timestamps': 'true',
            'variables': '{"input":{"attribution_id_v2":"ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,via_cold_start,1765909558185,660688,250100865708545,,","is_tracking_encrypted":false,"subscribe_location":"PROFILE","subscribee_id":"'+USERID+'","tracking":null,"actor_id":"'+self.session.user_id+'","client_mutation_id":"2"},"scale":1}',
            'doc_id': self.docid,
        }
        return payload
    def build_LikePage(self, PAGEID: str, doc_id='null'):
        if doc_id == 'null':
            self.docid = '25463905889878308'
        else:
            self.docid = doc_id
        payload = {
            'av': self.session.user_id,
            '__user': self.session.user_id,
            '__req': NumberEncoder.to_base36(self.request_counter),
            '__rev': self.session.revision,
            'fb_dtsg': self.session.token,
            'jazoest': self.session.jazoest,
            'lsd': self.session.lsd,
            '__spin_r': self.session.revision,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'CometProfilePlusLikeMutation',
            'server_timestamps': 'true',
            'variables': '{"input":{"is_tracking_encrypted":false,"page_id":"'+PAGEID+'","source":null,"tracking":null,"actor_id":"'+self.session.user_id+'","client_mutation_id":"4"},"scale":1}',
            'doc_id': self.docid,
        }
        return payload

class FB_API:
    def __init__(self, cookie: str):
        self.cookie = cookie
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        self.session = FacebookSession(cookie)
        self.payload_builder = None
        self.ready = False

    def login(self) -> bool:
        if not self.session.authenticate():
            return False
        self.payload_builder = GenData(self.session)
        self.ready = True
        self.header = {
            "accept": "*/*",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.facebook.com",
            "referer": "https://www.facebook.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": self.ua,
            "x-fb-lsd": self.session.lsd,
            "cookie": self.cookie,
            'x-fb-friendly-name': 'CometUFIFeedbackReactMutation',
        }
        return True

    def REACTION(self, REACTION: str, Id_post: str, doc_id: str = 'null'):
        if not isinstance(REACTION, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(Id_post, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(doc_id, str):
            return {"success": False, "error": "Value error"}
        try:
            if not self.ready:
                if not self.login():
                    return {"success": False, "error": "Not logged in"}
            payload = self.payload_builder.build_REACTION(REACTION, Id_post, doc_id)
            if 'err' in payload and payload['err']:
                return payload

            response = requests.post('https://www.facebook.com/api/graphql/', headers=self.header, data=payload)
            feedback_get_id = response.json().get('data', {}).get('feedback_react', {})
            if response.status_code == 200:
                if feedback_get_id:
                    feedback_get_id_1 = feedback_get_id.get('feedback', {})
                    feedback_id = feedback_get_id_1.get('id')
                    reaction_count = feedback_get_id_1.get('i18n_reaction_count')
                    return {"success": True, "error": None, "feedback_id": str(feedback_id), "reaction_count": str(reaction_count)}
                else:
                    return {"success": False, "error": str(response.json())}
            else:
                return {"success": False, "error": str(response.status_code)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def CMT(self, cmt: str, Id_post: str, Group_id: str = 'null', doc_id: str = 'null'):
        if not isinstance(cmt, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(Id_post, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(Group_id, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(doc_id, str):
            return {"success": False, "error": "Value error"}
        try:
            if not self.ready:
                if not self.login():
                    return {"success": False, "error": "Not logged in"}
            payload = self.payload_builder.build_CMT(cmt, Id_post, Group_id, doc_id)

            if 'err' in payload and payload['err']:
                return payload
            response = requests.post('https://www.facebook.com/api/graphql/', headers=self.header, data=payload)
            cmt_get_id = response.json().get('data', {}).get('comment_create', {})
            match = re.search(
                r"'comment'\s*:\s*\{[^}]*?'url'\s*:\s*'([^']+)'",
                str(response.json())
            )
            if response.status_code == 200:
                if cmt_get_id and match:
                    total_count = cmt_get_id.get('feedback', {}).get('comment_rendering_instance', {}).get('comments', {}).get('total_count', {})
                    comment_url = match.group(1)
                    return {"success": True, "error": None, "total_count": total_count, "comment_url": comment_url}
                else:
                    return {"success": False, "error": str(response.json())}
            else:
                return {"success": False, "error": str(response.status_code)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def FOLLOW(self, Id_post: str, doc_id: str = 'null'):
        if not isinstance(Id_post, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(doc_id, str):
            return {"success": False, "error": "Value error"}
        try:
            if not self.ready:
                if not self.login():
                    return {"success": False, "error": "Not logged in"}
            payload = self.payload_builder.build_Follow(Id_post, doc_id)
            if 'err' in payload and payload['err']:
                return payload
            response = requests.post('https://www.facebook.com/api/graphql/', headers=self.header, data=payload)
            pattern = r'"profile_owner"\s*:\s*\{[^}]*?"id"\s*:\s*"(\d+)"'
            match = re.search(pattern, str(response.json()))

            if response.status_code == 200:
                if match:
                    return {"success": True, "error": None, "id": match.group(1)}
                else:
                    return {"success": False, "error": str(response.json())}
            else:
                return {"success": False, "error": str(response.status_code)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def LIKE_PAGE(self, PAGE_ID: str, doc_id: str = 'null'):
        if not isinstance(PAGE_ID, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(doc_id, str):
            return {"success": False, "error": "Value error"}
        try:
            if not self.ready:
                if not self.login():
                    return {"success": False, "error": "Not logged in"}
            payload = self.payload_builder.build_LikePage(PAGE_ID, doc_id)
            if 'err' in payload and payload['err']:
                return payload
            response = requests.post('https://www.facebook.com/api/graphql/', headers=self.header, data=payload)
            
            if response.status_code == 200:
                return {"success": True, "error": None, "id": PAGE_ID}
            else:
                return {"success": False, "error": str(response.status_code)}
        except Exception as e:
            return {"success": False, "error": str(e)}
