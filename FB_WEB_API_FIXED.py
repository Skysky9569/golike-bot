import requests
import json
import time
import random
import mimetypes
import re,base64
from typing import Dict, Any, Optional
import uuid
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
    # Fallback doc_ids cho Like Page mutation (cập nhật thủ công khi FB thay đổi)
    _FALLBACK_DOC_IDS = [
        'null',
        '8522301131154562',
        '7894146167406836'
    ]
    # Fallback doc_ids cho CometPageLikeButtonMutation (Like Page - Thích trang)
    _LIKE_PAGE_DOC_IDS = [
        '24681394398162286',  # doc_id hợp lệ hiện tại (xác nhận 2025)
        '6390606484378696',
        '7024407287661374',
    ]
    # Cache doc_id để tránh scan lại mỗi lần
    _cached_like_page_doc_id: Optional[str] = None

    def __init__(self, cookie: str, proxies: dict = None):
        self.cookie = cookie
        self.proxies = proxies
        self.token = None
        self.user_id = None
        self.revision = None
        self.jazoest = None
        self.lsd = None
        self.reaction_doc_id: Optional[str] = None  # Được set sau authenticate()

    @classmethod
    def _find_doc_id_from_html(cls, html: str, proxies=None) -> Optional[str]:
        """Quét JS bundle của FB để tìm doc_id của CometUFIFeedbackReactMutation."""
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        # JS URL có thể bị escape kiểu https:\/\/static.xx.fbcdn.net...
        js_urls_raw = re.findall(r'"(https:\\/\\/static\.xx\.fbcdn\.net\\/rsrc\.php\\/[^"]{10,}\.js)"', html)
        if not js_urls_raw:
            # Dự phòng trường hợp không bị escape
            js_urls_raw = re.findall(r'"(https://static\.xx\.fbcdn\.net/rsrc\.php/[^"]{10,}\.js)"', html)
            
        js_urls = [url.replace('\\/', '/') for url in js_urls_raw]

        # Lặp qua 50 file JS đầu tiên (thay vì 25 vì FB có rất nhiều bundle)
        for url in js_urls[:50]:
            try:
                r = requests.get(url, headers={'user-agent': ua}, timeout=8, proxies=proxies)
                text = r.text
                # Pattern 1: CometUFIFeedbackReactMutation","123456789"
                m = re.search(r'CometUFIFeedbackReactMutation[^\d]{0,30}(\d{15,20})', text)
                if not m:
                    # Pattern 2: "123456789","CometUFIFeedbackReactMutation"
                    m = re.search(r'(\d{15,20})[^\d]{0,30}CometUFIFeedbackReactMutation', text)
                if m:
                    return m.group(1)
            except Exception:
                continue
        return None

    @classmethod
    def _find_like_page_doc_id(cls, html: str, proxies=None) -> Optional[str]:
        """Quét JS bundle của FB để tìm doc_id của CometPageLikeButtonMutation."""
        ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        js_urls_raw = re.findall(r'"(https:\\/\\/static\.xx\.fbcdn\.net\\/rsrc\.php\\/[^"]{10,}\.js)"', html)
        if not js_urls_raw:
            js_urls_raw = re.findall(r'"(https://static\.xx\.fbcdn\.net/rsrc\.php/[^"]{10,}\.js)"', html)
        js_urls = [url.replace('\\/', '/') for url in js_urls_raw]

        # Tên mutation cần tìm doc_id
        MUTATION_NAMES = [
            'CometPageLikeButtonMutation',
            'CometPageLikeMutation',
            'PageLikeMutation',
        ]
        for url in js_urls[:80]:
            try:
                r = requests.get(url, headers={'user-agent': ua}, timeout=8, proxies=proxies)
                text = r.text
                for mut in MUTATION_NAMES:
                    m = re.search(rf'{re.escape(mut)}[^\d]{{0,30}}(\d{{15,20}})', text)
                    if not m:
                        m = re.search(rf'(\d{{15,20}})[^\d]{{0,30}}{re.escape(mut)}', text)
                    if m:
                        return m.group(1)
            except Exception:
                continue
        return None

    def authenticate(self) -> dict:
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "max-age=0",
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
                timeout=30,
                proxies=self.proxies,
            )
            html = response.text
            self.token = HTMLExtractor.extract_token(html)
            self.user_id = HTMLExtractor.extract_user_id(html)
            self.revision = HTMLExtractor.extract_revision(html) or "1000000"
            self.jazoest = HTMLExtractor.extract_jazoest(html) or "0"
            self.lsd = HTMLExtractor.extract_lsd(html) or "0"
            if not self.token or not self.user_id:
                return {'err': 'Không thể lấy token hoặc user_id - cookie có thể hết hạn'}

            # Mặc định dùng 'null' để tránh quét JS bundle làm chậm tiến trình và tốn băng thông proxy
            self.reaction_doc_id = 'null'

            return {
                "token": self.token,
                "user_id": self.user_id,
                "revision": self.revision,
                "jazoest": self.jazoest,
                "lsd": self.lsd,
                "reaction_doc_id": self.reaction_doc_id,
            }
        except Exception as e:
            return {'err': f'Lỗi {str(e)}'}

class GenData:
    def __init__(self, session: FacebookSession):
        self.session = session
        self.request_counter = 0
    
    def build_REACTION(self, reaction: str, ID_POST: str, doc_id: str = 'null') -> Dict[str, Any]:
        if doc_id == 'null':
            self.docid = '24198888476452283'
        else:
            self.docid = doc_id
        self.request_counter += 1
        reaction_id_list = [1635855486666999,1678524932434102,613557422527858,115940658764963,478547315650144,908563459236466,444813342392137,'ERR']
        reaction_id_= reaction_id_list[0] if reaction == "LIKE" else reaction_id_list[1] if reaction == "LOVE" else reaction_id_list[2] if reaction == 'CARE' else  reaction_id_list[3] if reaction  == 'HAHA' else reaction_id_list[4] if reaction == 'WOW' else reaction_id_list[5] if reaction == 'SAD' else reaction_id_list[6] if reaction == 'ANGRY' else reaction_id_list[7]
        if reaction_id_ == "ERR" :
            return {'err' : 'Không Thể Sử Dụng Loại Cảm Xúc Này'}

        s = "feedback:"+str(ID_POST)
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

    def build_PiC(self,filename):
        try:
            subname = mimetypes.guess_type(filename)[0]
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "cache-control": "max-age=0",
                "cookie": self.session.cookie,
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            }
            params = {
                'av': self.session.user_id,
                '__aaid': '0',
                '__user': self.session.user_id,
                '__a': '1',
                '__req': '3o',
                '__hs': '20438.HYP:comet_pkg.2.1...0',
                'dpr': '1',
                '__ccg': 'EXCELLENT',
                '__rev': self.session.revision,
                '__s': 'cbrikq:ac7kkv:8obh3z',
                '__hsi': '7584526071696689530',
                '__dyn': '7xeUjGU9k9wxxt0koC8G6Ejh941twWwIxu13wFw_DyUJ3odF8vyUco5S3O2Saxa1NwJwpUe8hw8u2a1sw9u0LVEtwMw6ywIK1Rwwwg8a8462mcw8a1TwgEcEhwGxu782lwj8bU9kbxS2617wnE6a1awhUC7Udo5qfK0zEkxe2GexeeDwkUtxGm2SU4i5oe8cEW4-5pUfEdbwxwhFVovUaU3qxW2-awLyESE7i3C223908O3216gjxebwHwKG4UrwFg2fK7oC1hxB0jUpwgUjz89oeefx6UabDzUiBG2OUqwjVqwLwHwa211wo83KwHwOyUqxG0HEC',
                '__csr': 'gbsaEQrs2b1d4nPMB5NApnkgyggEtkIr9R4lsGuIpOhdGzFi9TiEgD5sBWi_lvj4bmFBGCAAyQKyviZPiO2jbPUBiXBKjSZWAlkDnbpmKk-iGtlTsDi9WnFV4N5ayeQAAh9aQ9VfaFbjD8h_L_RWjF5Z7iyV9pLXCHyknHVWqAt6VGKHFuHnV2222lUxpF9Ux9rLCFXFRXJ7AJKUDVlJqigBrDmjWQcCJGGGiinyAGKCTDiKHyAAeOvgymnKiaz-WBK8SaCh9penG9KiARiy-EGmiFJd24GjBH9BRyoyiQmdK9ABAzubjrCDxihe_LGQFFrxiqtt96gShz4qbVV4QrmaVGAJumaGXQqQqidAKGK5p8Ku9m8y9QnAiUkgBeuiEylvD-q9m4EmG8BDyKuXG-ah8x3XzKmVToc4cQCegqyDV8Gi58O8gyF4Jbx6aoizUKiElx7AgnBDyElx2iV68Km6oG2m5Edpp9m8BxmcyVrCyeECdABCg-9yEiCxPyk3J16ufgmjxqii4p8vDDACKqqeADzUhU-HggVE6W5Fof8C2i15Fy8C4UO5ogxO0Do5WdGA2268lg5Km5A5ojwUwCyWDxa8-K3y2t0PAyE4O32axC6EiUSqbK9y_iDF0Ag5m4KV7joGqdzbGcxaH8m9YylswK6ooUtg_zFotBAWnyonoS3eiEF2UCt0AXx8HRomgGm2h2Emm3C2h0LxmcxKeDoy6UynBGFFaqxi6AewFgW32t0wxCjXAy-UWFo8UgxS7VeU9E88l-9gqDDo3_wsUtw1pS05L426hTAz259zd5p40BGwnE1080SS0zA0yEaodbz8jwWwBK2Ra2m68nxX80c1w8q05bo492Enw53CgG16wu-0qm2K19nG6E0FG0lC8U2tF011-0aIw11msAE0cRo0axo5C320vwFU09qQuaw0w7wlE2_wL80hdw5BDg9UOu1Ec0W84e2Ly9TwcYxEB2Q1Yw8oM0S128C1gwXo142123ZxG2O04QE4Rw2s8kP3U7Za1Dyo2Ry40yQm0v9fx5G1wwjo1bEy1fwfu6d2C0kBwci0YQ2S0xFT50bi681xo6S2S6UCAqeaA3ei0AAi1Iyp2w9xw2Eopw4oo5Iw9FEW164aIiLuN8ye67wCx-0Wo-5ESaU0spEU0ieg8Vo0z-9S3y0ie0xk1kwgUgyFQ5998nw8C1Hy301HShwlolw821SwYwMooyDw115G5k6cw5la2a0cYo3Hw4Tg1y85y3Ku6EgybQexm0egyxm9gO7Q6IIQZO6hi0lG_g3m87oy9gO9wu86G0UE20wmE0By1vxC',
                '__hsdp': 'g4EwWgt12CAgacW2y58qwMyE4OE5p0FiqphG8xy6NVAzMB4Xkpq2kc9Sg5BPgB2l8l2o-qixG1j9PEbOO48B5W5Fph28IfOOBT5hryQmjrh2jckydPMx8yqqD8Wht8ihmpFIQj2h0AWuwCaaAZ8sDj9bDkix4bN2sxn2kcP9Eh6y8GCHEiax5zkxsQBgAQyJpa8GbqXpnBtJEx4AOBpqCGoF3CBFagxpFxyQJEcSjBiulhVarihd39Cskf4BeO4mQrXFKFupDiBmEGxd5AF4iGAoMDKHcgzienyQZCpYyaiXh6y7pqGF9kyIxTBaAKkHhZkxIzyBF4dHkoggl54KqpOAyEGFAFazXAAAK4y5iKl3SinhACx0CUB9qABWExRyqiyNgCOyFbAgK43GXEMiDrj6kh0woShh8-heHgx4ppQl4gkK4ouJ7V9V9pEy4oigGmFEK315RyUbucO38-nm5kn-yCwwpUXyVUSlWUJ9ipUMqVpS8HxynwLCwFgqG6VZpogG3iby8aUa4uEybzEdE82wjk6k69Quax3wlFUgwFxa1mx6m7e2Ba1lx-dIwGeUfUcohAqcKxfhfg8U88fU8oGi12ogxq7UkgkGewzyUG7Q45O0zG8U9HwxK12xC5qUowOBBglxSElHQ3-2ieGm2Wl2V2wzxGGxe3m0zLoa9VojOqXzUhxe3Kq3KvwPK4u1xAJ289pUow991aehQEmorBwfa5U2twko4-3e0QE5Ku8wgocUqwwwg84Sm7U6G6EswHwai9whEdE7C3K1fwNwIwzx_giwwwSzEd866dwcS2Ki0pi2q7Ebo1hU6214www-xu7oKby8eEcU4e0z83rx-0DU1gVo2cwhk6U6h0gE9EoyE9E-m68dofofUcUeUG48727osxK1hwiU4y0h64oow8e6E8qyEgzo42U31w9a0OQ1qwzxS10wm8cU662y7o26wXwkooK68nxq1Gx61Qz415xN387i3G321Fwio3ewAws8fEf8bi0vAey84G2W4Unw9Cbw8y2bw9mi16CxB0QAw8G1xwqUnwAx20AUuwLxGewn418w8q0BUrw',
                '__hblp': '1yegb8ijIkjh8eUeocU8U96aw961bwBxi5Ejy9HU5K1iw9G2e6EcUnG3y1MK5ojAwOgaUaU22wzxC3G4o5F1TWBxu5qg6Wax2i12Wmbz8gABUJi1e6UhKicx6i5FWxybzo8e2ny8O0yU9V85SfGi5E8WwFxnyoryEy1Ry8hwooa8423W0BK9wXwBUkxq0HFUbWwzwRxS585S2q7UpzUyq222-fCKuaBx26-5Eepo2Ix6m3oC2-3e5qxO1twci2-3e326EDwUy8y5UWdwEDy89U650AwSghxa6EoBwBxu2y2aQ2OFEy224E50w8Utxq48a9o29wTwcq4o46em6E4y8gdEowAwYxibCy8jxu6UK0zE43z85q5UcU9E6iUqwQCyEjzoS7824x-E4G49UrwKK1awwxy8yE4q6FovyUmwiEd8aUtwwGmU9Uc82awKwgF8tyoaEcpF98pzoW4o88bK4U9obEW6Q6EC3u1DyEO58eooxe2KK1owwwHwzx-7o3iy8y6U7y1hwm8qy8dFEgx62Sfxa58wwd8a8myUy2e5E9UswOwionG2u2aEpwhUC9wDxu7UcE4a2CcwQwEwOwlEcEjxui8wjUpUO3y8grwlU9UObzUkx68zUGaxKUKmu48vyUC33LwKwGwn8pyu2l3poC9gkxi8xO8wQwLwiaxueUkyEa8fEkwFwh9olyohxy68S12zUC6EW2248S4A78jxi1ewCgdo6y2C3u0AQ2m5Qm3CfxTxG9y4cwTxe3e5lwhSi2acx25Uyah8ixi8xqqmax-48K1uK645Euxy3iqcyo5G4ECmbomgbohyByA5V5gowVwiEZe8G1qUO3OTO0sUnwygnCCG49GzXwNwGwwxSUgU9rwF82a3iq7QaK8x-dCh8-10UlU7K7oK3e5ofE98G2C362auV8O4U9pEpm8ga98K1oCxV39J163eU5yqbxu2iUOEqwwCgC6oaaC84oW226FVEgwzxzz418w8q8UuyKewhU9o',
                '__sjsp': 'g4EwWgt12CAgacW2y58qwMyE4OE5p0FiqphG8xy6NVAzB94NeR6mxch5N5dSgr5NchsQ9ihJ8l2omD6E5cDewLb8gyknEmBB48yM-yi6T5iOKcBCgEAFD8m_xxAuQFSiEx9oBatFxl1ifxm8gFkFANhnj8utojwxqhVE8QP9EgcgjDCwAgVaqIQB1p0BLACup94zbLU94pwGCgp3eeJ257AKmAu3pyP6hXhEF4yFCtal4zx55Dgy78yP48i74epZ4xpzkcDCEwtzyzAooifx6hk3NOwJwYpAq5QcgcA59oc8C6V4bwkk350bJ07LwmU2zwkU7a0ji0jzwFg2am0sx0n4',
                '__comet_req': '15',
                'fb_dtsg': self.session.token,
                'jazoest': self.session.jazoest,
                'lsd': self.session.lsd,
                '__spin_r': self.session.revision,
                '__spin_b': 'trunk',
                '__spin_t': '1765910087',
                '__crn': 'comet.fbweb.CometHomeRoute',
            }
            _file_handle = open(filename,"rb")
            files = {
                'source': (None, '8'),
                'profile_id': (None, self.session.user_id),
                'waterfallxapp': (None, 'comet'),
                'farr': (filename, _file_handle, subname),
                'upload_id': (None, 'jsc_c_16'),
            }
            response = requests.post(
             'https://upload.facebook.com/ajax/react_composer/attachments/photo/upload',
                params=params,
                headers=headers,
                files=files,
            )
            r = response.text.replace("for (;;);","")
            json_ = json.loads(r)
            _file_handle.close()
            if 'payload' in json_ and 'photoID' in json_['payload']:
                return json_['payload']['photoID']
            else:
                return {'err': 'Không tìm thấy photoID trong response'}
        except Exception as e:
            try:
                _file_handle.close()
            except:
                pass
            return {'err' : f'Lỗi {str(e)}'}
    def build_CMT(self, cmt : str, ID_POST:str , Group_id : str ,doc_id = 'null') -> Dict[str, Any]:
        if doc_id == 'null':
            self.docid = '24615176934823390'
        else:
            self.docid = doc_id
        self.request_counter += 1
        s = "feedback:"+str(ID_POST)
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
            'fb_api_req_friendly_name': 'CometUFICreateCommentMutation',
            'server_timestamps': 'true',
            'variables': '{"feedLocation":"DEDICATED_COMMENTING_SURFACE","feedbackSource":110,"groupID":'+Group_id+',"input":{"client_mutation_id":"3","actor_id":"'+self.session.user_id+'","attachments":null,"feedback_id":"'+self.idpost+'","formatting_style":null,"message":{"ranges":[],"text":"'+cmt+'"},"attribution_id_v2":"CometHomeRoot.react,comet.home,unexpected,1765906156209,334250,4748854339,,;CometPhotoRoot.react,comet.mediaviewer.photo,via_cold_start,1765906141242,783051,,82,","vod_video_timestamp":null,"is_tracking_encrypted":true,"tracking":[],"feedback_source":"DEDICATED_COMMENTING_SURFACE","idempotence_token":"client:'+str(uuid.uuid4())+'","session_id":"'+str(uuid.uuid4())+'"},"inviteShortLinkKey":null,"renderLocation":null,"scale":1,"useDefaultActor":false,"focusCommentID":null,"__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false}',
            'doc_id': self.docid,
        }
        return payload
    def build_Follow(self,USERID:str, doc_id = 'null'):
        if doc_id == 'null':
            self.docid = '32658454793801856'
        else:
            self.docid = doc_id
        self.request_counter += 1
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
        """
        Build payload cho CometPageLikeButtonMutation.
        (GraphQL fallback — dùng khi fan_status.php thất bại)
        """
        self.docid = doc_id if doc_id != 'null' else '24681394398162286'
        self.request_counter += 1
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
            'fb_api_req_friendly_name': 'CometPageLikeButtonMutation',
            'server_timestamps': 'true',
            'variables': '{"input":{"is_tracking_encrypted":false,"page_id":"' + PAGEID + '","source":"timeline","tracking":null,"actor_id":"' + self.session.user_id + '","client_mutation_id":"1"},"scale":1}',
            'doc_id': self.docid,
        }
        return payload

    def build_LikePage_legacy(self, PAGEID: str) -> dict:
        """
        Build payload cho endpoint legacy fan_status.php.
        Đây là cách LIKE PAGE (Thích trang) ổn định nhất, không cần doc_id.
        Response format: for (;;);{"payload":{...},"jsmods":{...}}
        """
        self.request_counter += 1
        return {
            'fan_page_id': PAGEID,
            'action': 'fan',         # 'fan' = like, 'unfan' = unlike
            'av': self.session.user_id,
            '__user': self.session.user_id,
            '__req': NumberEncoder.to_base36(self.request_counter),
            '__rev': self.session.revision,
            'fb_dtsg': self.session.token,
            'jazoest': self.session.jazoest,
            'lsd': self.session.lsd,
            '__spin_r': self.session.revision,
            '__a': '1',
        }

    def build_post(self,TEXT :str , PHOTO, GROUP, doc_id = 'null'):
        self.fb_api_req_friendly_name = 'ComposerStoryCreateMutation'
        self.request_counter += 1
        if doc_id == 'null':
            self.docid = '25312274141763468'
        else:
            self.docid = doc_id
        if PHOTO != 'null' and GROUP == 'null':
            photo_id = self.build_PiC(PHOTO)
            if isinstance(photo_id, dict) and 'err' in photo_id:
                return photo_id
            var = '{"input":{"composer_entry_point":"inline_composer","composer_source_surface":"newsfeed","composer_type":"feed","idempotence_token":"'+str(uuid.uuid4())+'_FEED","source":"WWW","audience":{"privacy":{"allow":[],"base_state":"EVERYONE","deny":[],"tag_expansion_state":"UNSPECIFIED"}},"message":{"ranges":[],"text":"'+TEXT+'"},"inline_activities":[],"text_format_preset_id":"0","publishing_flow":{"supported_flows":["ASYNC_SILENT","ASYNC_NOTIF","FALLBACK"]},"reels_remix":{"is_original_audio_reusable":true,"remix_status":"DISABLED"},"attachments":[{"photo":{"id":"'+str(photo_id)+'"}}],"logging":{"composer_session_id":"'+str(uuid.uuid4())+'"},"navigation_data":{"attribution_id_v2":"CometHomeRoot.react,comet.home,tap_tabbar,1765910390697,887073,4748854339,,"},"tracking":[null],"event_share_metadata":{"surface":"newsfeed"},"actor_id":"'+self.session.user_id+'","client_mutation_id":"3"},"feedLocation":"NEWSFEED","feedbackSource":1,"focusCommentID":null,"gridMediaWidth":null,"groupID":null,"scale":1,"privacySelectorRenderLocation":"COMET_STREAM","checkPhotosToReelsUpsellEligibility":true,"renderLocation":"homepage_stream","useDefaultActor":false,"inviteShortLinkKey":null,"isFeed":true,"isFundraiser":false,"isFunFactPost":false,"isGroup":false,"isEvent":false,"isTimeline":false,"isSocialLearning":false,"isPageNewsFeed":false,"isProfileReviews":false,"isWorkSharedDraft":false,"hashtag":null,"canUserManageOffers":false,"__relay_internal__pv__CometUFIShareActionMigrationrelayprovider":true,"__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider":true,"__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider":true,"__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider":false,"__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false,"__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider":false,"__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider":true,"__relay_internal__pv__FeedDeepDiveTopicPillThreadViewEnabledrelayprovider":false,"__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider":true,"__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider":false,"__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider":false,"__relay_internal__pv__IsMergQAPollsrelayprovider":false,"__relay_internal__pv__FBReels_enable_meta_ai_label_gkrelayprovider":true,"__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider":true,"__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider":true,"__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider":true,"__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider":150,"__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider":false,"__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider":false,"__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV1relayprovider":false,"__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV2relayprovider":false}'
        elif PHOTO == 'null' and GROUP != 'null':
            var = '{"input":{"composer_entry_point":"inline_composer","composer_source_surface":"group","composer_type":"group","logging":{"composer_session_id":"'+str(uuid.uuid4())+'"},"source":"WWW","message":{"ranges":[],"text":"'+TEXT+'"},"with_tags_ids":null,"inline_activities":[],"text_format_preset_id":"0","group_flair":{"flair_id":null},"composed_text":{"block_data":["{}"],"block_depths":[0],"block_types":[0],"blocks":["test"],"entities":["[]"],"entity_map":"{}","inline_styles":["[]"]},"navigation_data":{"attribution_id_v2":"CometGroupDiscussionRoot.react,comet.group,via_cold_start,1766479285443,369314,2361831622,,"},"tracking":[null],"event_share_metadata":{"surface":"newsfeed"},"audience":{"to_id":"'+str(GROUP)+'"},"actor_id":"'+str(self.session.user_id)+'","client_mutation_id":"2"},"feedLocation":"GROUP","feedbackSource":0,"focusCommentID":null,"gridMediaWidth":null,"groupID":null,"scale":1,"privacySelectorRenderLocation":"COMET_STREAM","checkPhotosToReelsUpsellEligibility":false,"renderLocation":"group","useDefaultActor":false,"inviteShortLinkKey":null,"isFeed":false,"isFundraiser":false,"isFunFactPost":false,"isGroup":true,"isEvent":false,"isTimeline":false,"isSocialLearning":false,"isPageNewsFeed":false,"isProfileReviews":false,"isWorkSharedDraft":false,"hashtag":null,"canUserManageOffers":false,"__relay_internal__pv__CometUFIShareActionMigrationrelayprovider":true,"__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider":true,"__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider":true,"__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider":false,"__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false,"__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider":false,"__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider":true,"__relay_internal__pv__FeedDeepDiveTopicPillThreadViewEnabledrelayprovider":false,"__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider":true,"__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider":false,"__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider":false,"__relay_internal__pv__IsMergQAPollsrelayprovider":false,"__relay_internal__pv__FBReels_enable_meta_ai_label_gkrelayprovider":true,"__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider":true,"__relay_internal__pv__FBUnifiedLightweightVideoAttachmentWrapper_wearable_attribution_on_comet_reels_qerelayprovider":false,"__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider":true,"__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider":true,"__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider":206,"__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider":false,"__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider":false,"__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider":true,"__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV1relayprovider":true,"__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV2relayprovider":false}'
            self.docid = '25312274141763468' if doc_id == 'null' else doc_id
            self.fb_api_req_friendly_name = 'ComposerStoryCreateMutation'
        elif PHOTO != 'null' and GROUP != 'null':
            photo_id = self.build_PiC(PHOTO)
            if isinstance(photo_id, dict) and 'err' in photo_id:
                return photo_id
            var = '{"input":{"composer_entry_point":"inline_composer","composer_source_surface":"group","composer_type":"group","logging":{"composer_session_id":"'+str(uuid.uuid4())+'"},"source":"WWW","message":{"ranges":[],"text":"'+TEXT+'"},"with_tags_ids":null,"inline_activities":[],"text_format_preset_id":"0","group_flair":{"flair_id":null},"attachments":[{"photo":{"id":"'+photo_id+'"}}],"composed_text":{"block_data":["{}"],"block_depths":[0],"block_types":[0],"blocks":[""],"entities":["[]"],"entity_map":"{}","inline_styles":["[]"]},"navigation_data":{"attribution_id_v2":"CometGroupDiscussionRoot.react,comet.group,via_cold_start,1766479285443,369314,2361831622,,"},"tracking":[null],"event_share_metadata":{"surface":"newsfeed"},"audience":{"to_id":"'+str(GROUP)+'"},"actor_id":"'+self.session.user_id+'","client_mutation_id":"3"},"feedLocation":"GROUP","feedbackSource":0,"focusCommentID":null,"gridMediaWidth":null,"groupID":null,"scale":1,"privacySelectorRenderLocation":"COMET_STREAM","checkPhotosToReelsUpsellEligibility":false,"renderLocation":"group","useDefaultActor":false,"inviteShortLinkKey":null,"isFeed":false,"isFundraiser":false,"isFunFactPost":false,"isGroup":true,"isEvent":false,"isTimeline":false,"isSocialLearning":false,"isPageNewsFeed":false,"isProfileReviews":false,"isWorkSharedDraft":false,"hashtag":null,"canUserManageOffers":false,"__relay_internal__pv__CometUFIShareActionMigrationrelayprovider":true,"__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider":true,"__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider":true,"__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider":false,"__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false,"__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider":false,"__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider":true,"__relay_internal__pv__FeedDeepDiveTopicPillThreadViewEnabledrelayprovider":false,"__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider":true,"__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider":false,"__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider":false,"__relay_internal__pv__IsMergQAPollsrelayprovider":false,"__relay_internal__pv__FBReels_enable_meta_ai_label_gkrelayprovider":true,"__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider":true,"__relay_internal__pv__FBUnifiedLightweightVideoAttachmentWrapper_wearable_attribution_on_comet_reels_qerelayprovider":false,"__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider":true,"__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider":true,"__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider":206,"__relay_internal__pv__ShouldEnableBakedInTextStoriesrelayprovider":false,"__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider":false,"__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider":true,"__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV1relayprovider":true,"__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV2relayprovider":false}'
            self.docid = '25312274141763468' if doc_id == 'null' else doc_id
            self.fb_api_req_friendly_name = 'ComposerStoryCreateMutation'
        else:
            photo_id = 'null'
            var =  '{"input":{"composer_entry_point":"inline_composer","composer_source_surface":"newsfeed","composer_type":"feed","idempotence_token":"'+str(uuid.uuid4())+'_FEED","source":"WWW","audience":{"privacy":{"allow":[],"base_state":"EVERYONE","deny":[],"tag_expansion_state":"UNSPECIFIED"}},"message":{"ranges":[],"text":"'+TEXT+'"},"inline_activities":[],"text_format_preset_id":"0","publishing_flow":{"supported_flows":["ASYNC_SILENT","ASYNC_NOTIF","FALLBACK"]},"reels_remix":{"is_original_audio_reusable":true,"remix_status":"DISABLED"},"logging":{"composer_session_id":"'+str(uuid.uuid4())+'"},"navigation_data":{"attribution_id_v2":"CometHomeRoot.react,comet.home,tap_tabbar,1765912581894,250430,4748854339,,"},"tracking":[null],"event_share_metadata":{"surface":"newsfeed"},"actor_id":"'+self.session.user_id+'","client_mutation_id":"2"},"feedLocation":"NEWSFEED","feedbackSource":1,"focusCommentID":null,"gridMediaWidth":null,"groupID":null,"scale":1,"privacySelectorRenderLocation":"COMET_STREAM","checkPhotosToReelsUpsellEligibility":true,"renderLocation":"homepage_stream","useDefaultActor":false,"inviteShortLinkKey":null,"isFeed":true,"isFundraiser":false,"isFunFactPost":false,"isGroup":false,"isEvent":false,"isTimeline":false,"isSocialLearning":false,"isPageNewsFeed":false,"isProfileReviews":false,"isWorkSharedDraft":false,"hashtag":null,"canUserManageOffers":false,"__relay_internal__pv__CometUFIShareActionMigrationrelayprovider":true,"__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider":true,"__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider":true,"__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider":false,"__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider":false,"__relay_internal__pv__IsWorkUserrelayprovider":false,"__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider":false,"__relay_internal__pv__TestPilotShouldIncludeDemoAdUseCaserelayprovider":false,"__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider":true,"__relay_internal__pv__FeedDeepDiveTopicPillThreadViewEnabledrelayprovider":false,"__relay_internal__pv__FBReels_enable_view_dubbed_audio_type_gkrelayprovider":true,"__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider":false,"__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider":false,"__relay_internal__pv__IsMergQAPollsrelayprovider":false,"__relay_internal__pv__FBReels_enable_meta_ai_label_gkrelayprovider":true,"__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider":true,"__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider":true,"__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider":true,"__relay_internal__pv__GroupsCometGYSJFeedItemHeightrelayprovider":150,"__relay_internal__pv__StoriesShouldIncludeFbNotesrelayprovider":false,"__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider":false,"__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV1relayprovider":false,"__relay_internal__pv__GHLShouldUseSponsoredAuctionLabelFieldNameV2relayprovider":false}',
        
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
            'fb_api_req_friendly_name': self.fb_api_req_friendly_name,
            'server_timestamps': 'true',
            'variables': var,
            'doc_id': self.docid,
        }
        return payload
class FB_API:
    def __init__(self, cookie: str, proxies: dict = None):
        self.cookie = cookie
        self.proxies = proxies
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        self.session = FacebookSession(cookie, proxies=proxies)
        self.payload_builder = None
        self.ready = False
    def login(self) -> bool:
        if self.ready:
            return True
        self.info = self.session.authenticate()
        if 'err' in self.info:
            return self.info
        self.payload_builder = GenData(self.session)
        self.ready = True
        self.header ={
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
            "cookie" : self.cookie,
            'x-fb-friendly-name': 'CometUFIFeedbackReactMutation',
        }
        # Header riêng cho JSON body request (dùng cho REACTION)
        self.json_header = {
            "accept": "*/*",
            "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "origin": "https://www.facebook.com",
            "referer": "https://www.facebook.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": self.ua,
            "x-fb-lsd": self.session.lsd,
            "cookie": self.cookie,
            "x-fb-friendly-name": "CometUFIFeedbackReactMutation",
        }
        return True

    @staticmethod
    def _format_error(response):
        try:
            text = response.text.strip()
            if not text:
                return f'Empty response (HTTP {response.status_code})'
            data = response.json()
            errors = data.get('errors', [])
            if errors:
                err = errors[0]
                return {
                    'message': err.get('message'),
                    'code': err.get('code'),
                    'api_error_code': err.get('api_error_code'),
                    'severity': err.get('severity'),
                    'summary': err.get('summary'),
                    'description': err.get('description'),
                    'fbtrace_id': err.get('fbtrace_id'),
                    'raw': str(err)
                }
            return str(data)
        except Exception:
            return f'HTTP {response.status_code}: {response.text[:200]}'

    def REACTION(self, REACTION: str, Id_post: str, doc_id: str = 'null'):
        """
        Gửi reaction cho bài viết.

        :param REACTION: Loại reaction (LIKE, LOVE, HAHA, WOW, SAD, ANGRY, CARE)
        :param Id_post: ID bài viết
        :param doc_id: Tùy chọn truyền doc_id thủ công (mặc định 'null' sẽ lấy tự động)
        """
        if not isinstance(REACTION, str):
            return {'success': False, 'error': 'Value error'}
        if not isinstance(Id_post, str):
            return {'success': False, 'error': 'Value error'}
        try:
            self.login()
            if not self.ready:
                return {'success': False, 'error': 'Not logged in'}
            payload = self.payload_builder.build_REACTION(REACTION, Id_post, doc_id)
            if isinstance(payload, dict) and 'err' in payload:
                return payload

            doc_id_used = payload.get('doc_id', '?')

            # Gửi form-encoded data= với doc_id (cách Facebook yêu cầu)
            response = requests.post(
                'https://www.facebook.com/api/graphql/',
                headers=self.header,
                data=payload,
                proxies=self.proxies
            )

            if response.status_code == 200:
                resp_text = response.text.strip()
                if not resp_text:
                    return {'success': False, 'error': f'Empty response (doc_id {doc_id_used} có thể hết hạn)'}
                try:
                    resp_json = response.json()
                except Exception:
                    return {'success': False, 'error': f'Non-JSON: {resp_text[:200]}'}

                feedback_get_id = resp_json.get('data', {}).get('feedback_react', {})
                if feedback_get_id:
                    fb_data = feedback_get_id.get('feedback', {})
                    return {
                        'success': True,
                        'error': None,
                        'feedback_id': str(fb_data.get('id', '')),
                        'reaction_count': str(fb_data.get('i18n_reaction_count', '')),
                    }
                else:
                    err = self._format_error(response)
                    return {'success': False, 'error': err}
            else:
                return {'success': False, 'error': f'HTTP {response.status_code}: {response.text[:200]}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def CMT(self,cmt:str,Id_post : str,Group_id:str = 'null', doc_id : str = 'null'):
        """
        Gửi bình luận hoặc trả lời bình luận.

        :param content: Nội dung bình luận
        :param target_id: ID bài viết (id_post) **hoặc** ID bình luận (id_comment)
        :param group_id: ID group (nếu comment trong group, mặc định 'null')
        :param doc_id: Document ID (mặc định 'null')
        """
        if not isinstance(cmt, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(Id_post, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(Group_id, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(doc_id, str):
            return {"success": False, "error": "Value error"}
        try:
            self.login()
            if not self.ready:
                return {"success": False, "error": "Not logged in"}
            payload = self.payload_builder.build_CMT(cmt,Id_post,Group_id, doc_id )
    
            if isinstance(payload, dict) and 'err' in payload:
                return payload
            response = requests.post('https://www.facebook.com/api/graphql/', headers=self.header, data=payload, proxies=self.proxies)
            if response.status_code == 200:
                cmt_get_id = response.json().get('data', {}).get('comment_create', {})
                match = re.search(
                    r'"comment"\s*:\s*\{[^}]*?"url"\s*:\s*"([^"]+)"',
                    response.text
                )
                if cmt_get_id and match:
                    total_count = cmt_get_id.get('feedback',{}).get('comment_rendering_instance',{}).get('comments',{}).get('total_count',{})
                    comment_url = match.group(1)
                    return {"success": True, "error" : None , "total_count" : total_count,"comment_url" : comment_url}
                else:
                    return {"success": False, "error" : self._format_error(response)}
            else:
                return {"success": False, "error" : str(response.status_code)}
        except Exception as e:
             return {"success": False, "error": str(e)}
    def FOLLOW(self,Id_post:str, doc_id:str = 'null'):
        """
        Theo dõi (follow) người dùng hoặc trang.

        :param target_id: ID người dùng / trang (user_id, page_id)
        :param doc_id: Document ID (mặc định 'null')
        """
        if not isinstance(Id_post, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(doc_id, str):
            return {"success": False, "error": "Value error"}
        try:
            self.login()
            if not self.ready:
                return {"success": False, "error": "Not logged in"}
            payload = self.payload_builder.build_Follow(Id_post, doc_id)
            if isinstance(payload, dict) and 'err' in payload:
                return payload
            response = requests.post('https://www.facebook.com/api/graphql/', headers=self.header, data=payload, proxies=self.proxies)
            if response.status_code == 200:
                pattern = r'"profile_owner"\s*:\s*\{[^}]*?"id"\s*:\s*"(\d+)"'
                match = re.search(pattern, response.text)
                if match:
                    return {"success": True, "error" : None , "id" : match.group(1)}
                else:
                    return {"success": False, "error" : self._format_error(response)}
            else:
                return {"success": False, "error" : str(response.status_code)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def LIKE_PAGE(self, PAGE_ID: str, doc_id: str = 'null'):
        """
        Like (Thích) một Facebook Fanpage.

        Chiến lược:
        1. PRIMARY: POST /ajax/pages/fan_status.php (không cần doc_id, ổn định)
        2. FALLBACK: GraphQL CometPageLikeButtonMutation (cần doc_id hợp lệ)

        :param PAGE_ID: ID của Facebook Page cần like
        :param doc_id: GraphQL doc_id (chỉ dùng cho fallback)
        """
        if not isinstance(PAGE_ID, str):
            return {"success": False, "error": "Value error"}
        try:
            self.login()
            if not self.ready:
                return {"success": False, "error": "Not logged in"}

            # ================================================
            # APPROACH 1: fan_status.php (legacy, không cần doc_id)
            # ================================================
            try:
                fan_payload = self.payload_builder.build_LikePage_legacy(PAGE_ID)
                fan_header = {
                    "accept": "*/*",
                    "accept-language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                    "content-type": "application/x-www-form-urlencoded",
                    "origin": "https://www.facebook.com",
                    "referer": f"https://www.facebook.com/profile.php?id={PAGE_ID}",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": self.ua,
                    "x-fb-lsd": self.session.lsd,
                    "cookie": self.cookie,
                    "x-requested-with": "XMLHttpRequest",
                }
                fan_resp = requests.post(
                    'https://www.facebook.com/ajax/pages/fan_status.php',
                    headers=fan_header,
                    data=fan_payload,
                    proxies=self.proxies,
                    timeout=15
                )
                if fan_resp.status_code == 200:
                    resp_text = fan_resp.text.strip()
                    # Response format: for (;;);{"payload":{...}}
                    clean = resp_text.replace('for (;;);', '').strip()
                    try:
                        rj = json.loads(clean)
                        # Kiểm tra lỗi
                        errors = rj.get('errors', []) or rj.get('error', [])
                        if errors:
                            err_str = str(errors)
                            print(f"[LIKE_PAGE] fan_status lỗi: {err_str[:120]}")
                        else:
                            # Thành công nếu không có error và có payload
                            payload_data = rj.get('payload', {})
                            if payload_data is not None:
                                print(f"[LIKE_PAGE] ✓ fan_status.php thành công (page_id={PAGE_ID})")
                                return {"success": True, "error": None, "id": PAGE_ID}
                            # payload = None cũng có thể OK (already liked)
                            print(f"[LIKE_PAGE] ✓ fan_status.php OK - đã like (payload=None có thể đã like trước)")
                            return {"success": True, "error": None, "id": PAGE_ID}
                    except json.JSONDecodeError:
                        # Nếu không parse được JSON nhưng HTTP 200 thì vẫn có thể OK
                        if 'errorDescription' not in resp_text and 'error_msg' not in resp_text:
                            print(f"[LIKE_PAGE] ✓ fan_status.php HTTP 200 (non-JSON response)")
                            return {"success": True, "error": None, "id": PAGE_ID}
                        print(f"[LIKE_PAGE] fan_status lỗi (non-JSON): {resp_text[:200]}")
                else:
                    print(f"[LIKE_PAGE] fan_status HTTP {fan_resp.status_code}")
            except Exception as e1:
                print(f"[LIKE_PAGE] fan_status exception: {e1}")

            # ================================================
            # APPROACH 2: GraphQL fallback (nếu fan_status thất bại)
            # ================================================
            print("[LIKE_PAGE] Thử GraphQL fallback...")
            doc_ids_to_try = [d for d in FacebookSession._LIKE_PAGE_DOC_IDS if d not in ('null', '25463905889878308')]
            last_error = None
            for try_doc_id in doc_ids_to_try:
                payload = self.payload_builder.build_LikePage(PAGE_ID, try_doc_id)
                if isinstance(payload, dict) and 'err' in payload:
                    continue
                response = requests.post(
                    'https://www.facebook.com/api/graphql/',
                    headers=self.header,
                    data=payload,
                    proxies=self.proxies,
                    timeout=15
                )
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    continue
                try:
                    resp_json = response.json()
                except Exception:
                    last_error = f"Non-JSON: {response.text[:200]}"
                    continue
                errors = resp_json.get("errors", [])
                if errors:
                    err_msg = errors[0].get("message", str(errors[0]))
                    last_error = f"FB GraphQL error (doc_id={try_doc_id}): {err_msg}"
                    print(f"[LIKE_PAGE] doc_id={try_doc_id} → {err_msg[:100]}")
                    continue
                data = resp_json.get("data", {})
                if data:
                    FacebookSession._cached_like_page_doc_id = try_doc_id
                    print(f"[LIKE_PAGE] ✓ GraphQL thành công (doc_id={try_doc_id})")
                    return {"success": True, "error": None, "id": PAGE_ID}
                last_error = f"data rỗng (doc_id={try_doc_id})"

            print(f"[LIKE_PAGE] ✗ Cả 2 phương pháp đều thất bại. Lỗi cuối: {last_error}")
            return {"success": False, "error": last_error or "All methods failed"}

        except Exception as e:
            return {"success": False, "error": str(e)}



    def POST(self,content : str,Photo :str = 'null',Group_id :str = 'null', doc_id : str = 'null'):
        """
        Đăng bài viết mới.

        :param content: Nội dung bài viết
        :param photo: URL hoặc đường dẫn ảnh (tùy hệ thống), None nếu không có ảnh
        :param group_id: ID group (nếu đăng trong group), None nếu đăng trang cá nhân
        :param doc_id: Document ID (mặc định None)
        """
        if not isinstance(content, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(Photo, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(Group_id, str):
            return {"success": False, "error": "Value error"}
        if not isinstance(doc_id, str):
            return {"success": False, "error": "Value error"}
        try:
            self.login()
            if not self.ready:
                return {"success": False, "error": "Not logged in"}
            payload = self.payload_builder.build_post(content,Photo,Group_id, doc_id )
    
            if isinstance(payload, dict) and 'err' in payload:
                return payload
            
            response = requests.post('https://www.facebook.com/api/graphql/', headers=self.header, data=payload, proxies=self.proxies)
            if response.status_code == 200:
                if Group_id != 'null':
                    idpost = re.search(r'"post_id"\s*:\s*"(\d+)"', response.text)
                else:
                    idpost = re.search(r'"post_id"\s*:\s*"(\d+)"', response.text)
                if idpost:
                    return {"success": True, "error" : None , "id" : idpost.group(1) }
                else:
                    return {"success": False, "error" : self._format_error(response)}
            else:
                return {"success": False, "error" : str(response.status_code)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        

    

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    # ============================================
    # DEMO: Hướng dẫn sử dụng FB_WEB_API
    # ============================================
    
    # 1. Khởi tạo với cookie Facebook
    COOKIE = "" # Đã xoá để bảo mật thông tin cá nhân
    fb = FB_API(COOKIE)
    
    # 2. Đăng nhập (chỉ cần gọi 1 lần, các method sẽ tự cache)
    result = fb.login()
    if isinstance(result, dict) and 'err' in result:
        print(f"[LỖI ĐĂNG NHẬP] {result['err']}")
    else:
        print(f"[OK] Đăng nhập thành công!")
        print(f"  - User ID: {fb.session.user_id}")
        print(f"  - Token: {fb.session.token[:20]}...")
        
        # 3. Reaction bài viết  
        # Loại: LIKE, LOVE, CARE, HAHA, WOW, SAD, ANGRY
        # result = fb.REACTION("LIKE", "POST_ID_HERE")
        # print(f"[REACTION] {result}")
        
        # 4. Comment bài viết
        # result = fb.CMT("Nội dung comment", "POST_ID_HERE")
        # print(f"[COMMENT] {result}")
        
        # 5. Follow người dùng
        # result = fb.FOLLOW("100044545834601")
        # print(f"[FOLLOW] {result}")

        # 6. Like Facebook Page
        result = fb.LIKE_PAGE("100063884511687")
        print(f"[LIKE_PAGE] {result}")
        
        # 6. Đăng bài
        # Đăng text thường:
        # result = fb.POST("Nội dung bài viết")
        # Đăng kèm ảnh:
        # result = fb.POST("Nội dung", Photo="path/to/image.jpg")
        # Đăng trong group:
        # result = fb.POST("Nội dung", Group_id="GROUP_ID")
        # Đăng ảnh trong group:
        # result = fb.POST("Nội dung", Photo="path/to/image.jpg", Group_id="GROUP_ID")
        # print(f"[POST] {result}")

        