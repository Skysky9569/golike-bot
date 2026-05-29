import time
import base64
import json
import sys
import os
import random
import urllib3
from FB_WEB_API_FIXED import FB_API

# Tự động chọn curl_cffi nếu có để giả lập JA3 fingerprint của trình duyệt Chrome bypass Cloudflare
try:
    from curl_cffi import requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests
    HAS_CURL_CFFI = False

# Tắt cảnh báo SSL Insecure cho requests truyền thống
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Fix emoji encoding trên Windows
sys.stdout.reconfigure(encoding='utf-8')

def http_get(url, **kwargs):
    """Wrapper thực hiện GET request sử dụng curl_cffi (Chrome impersonate) hoặc requests thường"""
    if HAS_CURL_CFFI:
        kwargs.setdefault('impersonate', 'chrome110')
    return requests.get(url, **kwargs)

def http_post(url, **kwargs):
    """Wrapper thực hiện POST request sử dụng curl_cffi (Chrome impersonate) hoặc requests thường"""
    if HAS_CURL_CFFI:
        kwargs.setdefault('impersonate', 'chrome110')
    return requests.post(url, **kwargs)


# 1. Cấu hình Headers và Params mặc định
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9,vi;q=0.8,fr-FR;q=0.7,fr;q=0.6',
    'authorization': 'Bearer ',  # Sẽ được cập nhật khi chạy
    'content-type': 'application/json;charset=utf-8',
    'origin': 'https://app.golike.net',
    'priority': 'u=1, i',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/148.0.0.0 Mobile/15E148 Safari/604.1',
}

FB_ID = ''
USERS_FB_ACCOUNT_ID = 0

PARAMS = {
    'fb_id': '',
    'server': 'sv2',
    'low_job': '1',
}

# ============ CẤU HÌNH DELAY (có thể thay đổi khi chạy) ============
DELAY_CONFIG = {
    'action_min': 5,       # Delay tối thiểu sau khi thực hiện hành động FB (giây)
    'action_max': 12,      # Delay tối đa sau khi thực hiện hành động FB (giây)
    'report_min': 5,       # Delay tối thiểu trước khi báo cáo job lên Golike (giây)
    'report_max': 10,      # Delay tối đa trước khi báo cáo job lên Golike (giây)
    'between_jobs_min': 8, # Delay tối thiểu giữa các job (giây)
    'between_jobs_max': 15,# Delay tối đa giữa các job (giây)
    'no_job_min': 15,      # Delay tối thiểu khi không có job (giây)
    'no_job_max': 30,      # Delay tối đa khi không có job (giây)
    'report_retry_delay': 5, # Delay khi báo cáo quá nhanh (giây)
    'report_max_retries': 3, # Số lần thử lại báo cáo tối đa
}

def input_delay_value(prompt, default):
    """Nhập giá trị delay với validation, trả về default nếu Enter."""
    try:
        val = input(prompt).strip()
        if not val:
            return default
        val = int(val)
        if val < 0:
            print("    Gia tri khong hop le, su dung mac dinh.")
            return default
        return val
    except ValueError:
        print("    Gia tri khong hop le, su dung mac dinh.")
        return default

def configure_delays():
    """Menu cấu hình delay min-max cho người dùng."""
    global DELAY_CONFIG
    print("\n--- CAU HINH DELAY (An Enter de dung mac dinh) ---")
    print(f"  Delay mac dinh: Action={DELAY_CONFIG['action_min']}-{DELAY_CONFIG['action_max']}s | "
          f"Report={DELAY_CONFIG['report_min']}-{DELAY_CONFIG['report_max']}s | "
          f"Jobs={DELAY_CONFIG['between_jobs_min']}-{DELAY_CONFIG['between_jobs_max']}s | "
          f"NoJob={DELAY_CONFIG['no_job_min']}-{DELAY_CONFIG['no_job_max']}s")
    
    custom = input("Ban co muon tuy chinh delay? (y/N): ").strip().lower()
    if custom != 'y':
        print("=> Su dung cau hinh delay mac dinh.")
        return
    
    print("\n  [1] Delay sau khi thuc hien hanh dong Facebook (like/follow/reaction):")
    DELAY_CONFIG['action_min'] = input_delay_value(f"      Min (mac dinh {DELAY_CONFIG['action_min']}s): ", DELAY_CONFIG['action_min'])
    DELAY_CONFIG['action_max'] = input_delay_value(f"      Max (mac dinh {DELAY_CONFIG['action_max']}s): ", DELAY_CONFIG['action_max'])
    if DELAY_CONFIG['action_max'] < DELAY_CONFIG['action_min']:
        DELAY_CONFIG['action_max'] = DELAY_CONFIG['action_min']
        print(f"      => Max da duoc chinh lai = Min = {DELAY_CONFIG['action_min']}s")

    print("\n  [2] Delay truoc khi bao cao job len Golike:")
    DELAY_CONFIG['report_min'] = input_delay_value(f"      Min (mac dinh {DELAY_CONFIG['report_min']}s): ", DELAY_CONFIG['report_min'])
    DELAY_CONFIG['report_max'] = input_delay_value(f"      Max (mac dinh {DELAY_CONFIG['report_max']}s): ", DELAY_CONFIG['report_max'])
    if DELAY_CONFIG['report_max'] < DELAY_CONFIG['report_min']:
        DELAY_CONFIG['report_max'] = DELAY_CONFIG['report_min']
        print(f"      => Max da duoc chinh lai = Min = {DELAY_CONFIG['report_min']}s")

    print("\n  [3] Delay giua cac job:")
    DELAY_CONFIG['between_jobs_min'] = input_delay_value(f"      Min (mac dinh {DELAY_CONFIG['between_jobs_min']}s): ", DELAY_CONFIG['between_jobs_min'])
    DELAY_CONFIG['between_jobs_max'] = input_delay_value(f"      Max (mac dinh {DELAY_CONFIG['between_jobs_max']}s): ", DELAY_CONFIG['between_jobs_max'])
    if DELAY_CONFIG['between_jobs_max'] < DELAY_CONFIG['between_jobs_min']:
        DELAY_CONFIG['between_jobs_max'] = DELAY_CONFIG['between_jobs_min']
        print(f"      => Max da duoc chinh lai = Min = {DELAY_CONFIG['between_jobs_min']}s")

    print("\n  [4] Delay khi khong co job:")
    DELAY_CONFIG['no_job_min'] = input_delay_value(f"      Min (mac dinh {DELAY_CONFIG['no_job_min']}s): ", DELAY_CONFIG['no_job_min'])
    DELAY_CONFIG['no_job_max'] = input_delay_value(f"      Max (mac dinh {DELAY_CONFIG['no_job_max']}s): ", DELAY_CONFIG['no_job_max'])
    if DELAY_CONFIG['no_job_max'] < DELAY_CONFIG['no_job_min']:
        DELAY_CONFIG['no_job_max'] = DELAY_CONFIG['no_job_min']
        print(f"      => Max da duoc chinh lai = Min = {DELAY_CONFIG['no_job_min']}s")

    print("\n  [5] Cau hinh bao cao (report):")
    DELAY_CONFIG['report_retry_delay'] = input_delay_value(f"      Delay khi bao cao qua nhanh (mac dinh {DELAY_CONFIG['report_retry_delay']}s): ", DELAY_CONFIG['report_retry_delay'])
    DELAY_CONFIG['report_max_retries'] = input_delay_value(f"      So lan thu lai bao cao toi da (mac dinh {DELAY_CONFIG['report_max_retries']}): ", DELAY_CONFIG['report_max_retries'])

    print("\n=> Cau hinh delay da cap nhat:")
    print(f"   Action:  {DELAY_CONFIG['action_min']}-{DELAY_CONFIG['action_max']}s")
    print(f"   Report:  {DELAY_CONFIG['report_min']}-{DELAY_CONFIG['report_max']}s")
    print(f"   Jobs:    {DELAY_CONFIG['between_jobs_min']}-{DELAY_CONFIG['between_jobs_max']}s")
    print(f"   No Job:  {DELAY_CONFIG['no_job_min']}-{DELAY_CONFIG['no_job_max']}s")
    print(f"   Retry:   {DELAY_CONFIG['report_retry_delay']}s x {DELAY_CONFIG['report_max_retries']} lan")

def random_delay(min_key, max_key, label=""):
    """Thực hiện delay ngẫu nhiên giữa min và max từ DELAY_CONFIG."""
    d = random.randint(DELAY_CONFIG[min_key], DELAY_CONFIG[max_key])
    if label:
        print(f"    {label} {d}s...")
    time.sleep(d)
    return d

def generate_t_token():
    """Tạo token 't' động dựa trên timestamp hiện tại (mã hóa Base64 3 lần)"""
    t = str(int(time.time()))
    for _ in range(3):
        t = base64.b64encode(t.encode('utf-8')).decode('utf-8')
    return t

def get_headers():
    """Lấy headers hoàn chỉnh với token 't' tự sinh động"""
    headers = HEADERS.copy()
    headers['t'] = generate_t_token()
    return headers

# ============ GOLIKE API FUNCTIONS ============

def get_facebook_accounts():
    """Lấy danh sách tài khoản Facebook liên kết từ Golike"""
    url = 'https://gateway.golike.net/api/fb-account?limit=200'
    try:
        response = http_get(url, headers=get_headers(), verify=False)
        try:
            res_json = response.json()
            if res_json.get('status') == 200 and res_json.get('success'):
                return res_json.get('data', {}).get('data', [])
            else:
                print(f"Loi lay danh sach tai khoan: {res_json.get('message', 'Khong ro nguyen nhan')}")
        except Exception:
            print(f"Loi phan hoi tu API (HTTP {response.status_code}): {response.text[:200]}")
    except Exception as e:
        print("Loi ket noi API lay danh sach tai khoan:", e)
    return []

def get_jobs():
    url = 'https://gateway.golike.net/api/advertising/publishers/get-jobs-2026'
    try:
        response = http_get(url, params=PARAMS, headers=get_headers(), verify=False)
        try:
            res_json = response.json()
            if res_json.get('status') == 200 and res_json.get('success'):
                return res_json.get('data', [])
            else:
                print(f"Loi Golike: {res_json.get('message', 'Khong ro nguyen nhan')}")
        except Exception:
            print(f"Loi phan hoi tu API Get Jobs (HTTP {response.status_code}): {response.text[:200]}")
    except Exception as e:
        print("Loi ket noi API Get Jobs:", e)
    return []

def report_job(job):
    """Gửi API báo cáo hoàn thành job lên Golike, tự retry nếu báo cáo quá nhanh."""
    url = 'https://gateway.golike.net/api/advertising/publishers/complete-jobs-2026'
    json_data = {
        'object_id': job['object_id'],
        'job_id': job['id'],
        'type': job['type'],
        'uid': FB_ID,
        'users_fb_account_id': USERS_FB_ACCOUNT_ID,
        'users_advertising_id': job['id'],
        'message': None,
    }
    max_retries = DELAY_CONFIG.get('report_max_retries', 3)
    retry_delay = DELAY_CONFIG.get('report_retry_delay', 5)
    
    for attempt in range(1, max_retries + 1):
        try:
            response = http_post(url, headers=get_headers(), json=json_data, verify=False)
            try:
                res_json = response.json()
                # In ra toàn bộ response từ API
                print(f"    [API Response] HTTP {response.status_code}: {json.dumps(res_json, ensure_ascii=False)}")
                
                if res_json.get('status') == 200 and res_json.get('success'):
                    msg = res_json.get('message', '')
                    print(f"    ✅ BAO CAO THANH CONG! {msg}")
                    return True
                else:
                    err_msg = res_json.get('message', '')
                    cooldown = res_json.get('cooldown', 0)
                    
                    # Lỗi có thể retry (quá nhanh / chưa thực hiện)
                    can_retry = ('quá nhanh' in err_msg or 'too fast' in err_msg.lower() 
                                 or 'chưa thực hiện' in err_msg or 'chua thuc hien' in err_msg.lower())
                    
                    if can_retry and attempt < max_retries:
                        # Ưu tiên dùng cooldown từ API, nếu không có thì dùng config
                        wait = max(cooldown, retry_delay) + random.randint(2, 5)
                        print(f"    ⏳ Cho {wait}s roi thu lai (lan {attempt}/{max_retries})...")
                        time.sleep(wait)
                        continue
                    elif can_retry:
                        print(f"    ❌ Bao cao that bai sau {max_retries} lan thu: {err_msg}")
                        return False
                    else:
                        print(f"    ❌ Bao cao that bai: {err_msg}")
                        return False
            except Exception:
                print(f"    [API Raw] HTTP {response.status_code}: {response.text[:300]}")
                return False
        except Exception as e:
            print(f"    Loi khi bao cao Job {job['id']}: {e}")
            return False
    return False

def skip_job(job):
    """Gửi API báo cáo bỏ qua/báo lỗi job lên Golike"""
    url = 'https://gateway.golike.net/api/report/send'
    json_data = {
        'description': 'Tôi không muốn làm Job này',
        'users_advertising_id': job['id'],
        'type': 'ads',
        'fb_id': FB_ID,
        'error_type': 0,
        'provider': 'facebook',
        'comment': None,
    }
    try:
        response = http_post(url, headers=get_headers(), json=json_data, verify=False)
        try:
            res_json = response.json()
            if res_json.get('status') == 200 and res_json.get('success'):
                print(f"    Da bao cao skip Job {job['id']} thanh cong!")
                return True
            else:
                print(f"    Bao cao skip Job that bai: {res_json.get('message', '')}")
                return False
        except Exception:
            print(f"    Loi phan hoi tu API Skip (HTTP {response.status_code}): {response.text[:200]}")
            return False
    except Exception as e:
        print(f"    Loi khi bao cao skip Job {job['id']}: {e}")
        return False

# ============ TOKEN PERSISTENCE ============

TOKEN_FILE = "golike_token.json"

def load_saved_token():
    """Đọc token đã lưu từ file."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('token', '')
        except Exception:
            pass
    return ''

def save_token(token):
    """Lưu token vào file để dùng lại."""
    try:
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            json.dump({'token': token}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Loi khi luu token: {e}")
        return False

def delete_saved_token():
    """Xóa token đã lưu."""
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            return True
        except Exception:
            pass
    return False

def mask_token(token):
    """Che bớt token để hiển thị an toàn."""
    if len(token) > 20:
        return token[:15] + "..." + token[-6:]
    return token

def configure_token():
    """Menu cấu hình token Golike với lưu/tải."""
    print("\n--- CAU HINH TOKEN GOLIKE ---")
    saved_token = load_saved_token()
    
    if saved_token:
        print(f"[✓] Tim thay token da luu: {mask_token(saved_token)}")
        print("[1] Su dung token da luu")
        print("[2] Nhap token moi (thay the token cu)")
        print("[3] Xoa token da luu va nhap moi")
        choice = input("Chon (mac dinh 1): ").strip()
        
        if choice == "3":
            delete_saved_token()
            print("Da xoa token cu.")
            token = input("Nhap Golike Bearer Token moi: ").strip()
            if not token:
                print("Token khong duoc de trong!")
                return None
        elif choice == "2":
            token = input("Nhap Golike Bearer Token moi: ").strip()
            if not token:
                print("Token khong duoc de trong!")
                return None
        else:
            token = saved_token
            print("=> Su dung token da luu.")
    else:
        print("[!] Chua co token nao duoc luu.")
        token = input("Nhap Golike Bearer Token: ").strip()
        if not token:
            print("Token khong duoc de trong!")
            return None
    
    # Chuẩn hóa token
    if not token.startswith("Bearer "):
        token = f"Bearer {token}"
    
    # Lưu token nếu là token mới
    if token != saved_token:
        save_choice = input("Luu token de lan sau khong can nhap lai? (Y/n): ").strip().lower()
        if save_choice != 'n':
            if save_token(token):
                print("=> Da luu token thanh cong!")
            else:
                print("=> Luu token that bai, se phai nhap lai lan sau.")
    
    return token

def load_local_accounts():
    """Đọc thông tin cookie từ single_mode_accounts.json"""
    filename = "single_mode_accounts.json"
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('accounts', [])
        except Exception as e:
            print(f"Loi doc file cookie {filename}: {e}")
    return []

# ============ JOB EXECUTION WITH FB_API ============

def resolve_post_id(fb_client, object_id, link):
    """
    Nếu object_id chứa ký tự chữ (ví dụ 'pfbid...'),
    thực hiện fetch link Facebook để lấy ID số (numeric ID) phục vụ cho GraphQL.
    """
    import re
    if object_id.isdigit():
        return object_id
        
    print(f"    [Resolve] Target ID '{object_id}' khong phai dang so. Dang phan giai tu link...")
    url = link.rstrip('#')
    mbasic_url = url.replace("www.facebook.com", "mbasic.facebook.com").replace("m.facebook.com", "mbasic.facebook.com")
    
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "cookie": fb_client.cookie
    }
    
    try:
        response = http_get(mbasic_url, headers=headers, verify=False, timeout=15)
        html = response.text
        
        patterns = [
            r'ft_ent_identifier=(\d+)',
            r'feedback_id":"(\d+)"',
            r'"top_level_post_id":"(\d+)"',
            r'id="like_(\d+)"',
            r'/reactions/picker/\?ft_ent_identifier=(\d+)',
            r'story\.php\?story_fbid=[^&]+&amp;id=(\d+)',
            r'photo\.php\?fbid=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                numeric_id = match.group(1)
                print(f"    [Resolve] ✓ Phan giai thanh cong ID so: {numeric_id}")
                return numeric_id
                
        # Fallback to www
        response = http_get(url, headers=headers, verify=False, timeout=15)
        html = response.text
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                numeric_id = match.group(1)
                print(f"    [Resolve] ✓ Phan giai thanh cong ID so (WWW): {numeric_id}")
                return numeric_id
                
    except Exception as e:
        print(f"    [Resolve] Loi khi phan giai ID: {e}")
        
    return object_id

def execute_job_via_web(fb_client, job):
    """Thực thi nhiệm vụ Facebook thông qua HTTP Web API"""
    job_id = job['id']
    job_type = job['type'].lower()
    object_id = job['object_id']
    link = job.get('link', '')

    # Phân giải post ID sang dạng số nếu cần
    object_id = resolve_post_id(fb_client, object_id, link)

    print(f"\n--- Dang xu ly Job {job_id} | Loai: {job_type} | Target ID: {object_id}")

    # Xử lý theo loại nhiệm vụ
    result = {'success': False, 'error': 'Chua xu ly loai job nay'}

    # 1. Nhóm Like Page (Thích trang)
    if 'like_page' in job_type or 'lik_page' in job_type:
        print("    -> Dang thuc hien LIKE_PAGE...")
        result = fb_client.LIKE_PAGE(object_id)

    # 2. Nhóm Follow / Subscribe (Theo dõi)
    elif 'follow' in job_type or 'sub' in job_type:
        print("    -> Dang thuc hien FOLLOW...")
        result = fb_client.FOLLOW(object_id)

    # 3. Nhóm Reactions biểu cảm đặc biệt
    elif any(r in job_type for r in ['love', 'care', 'haha', 'wow', 'sad', 'angry']):
        for r in ['love', 'care', 'haha', 'wow', 'sad', 'angry']:
            if r in job_type:
                reaction_upper = r.upper()
                print(f"    -> Dang thuc hien bieu cam {reaction_upper}...")
                result = fb_client.REACTION(reaction_upper, object_id)
                break

    # 4. Nhóm Like bài viết mặc định
    elif 'like' in job_type:
        print("    -> Dang thuc hien LIKE bai viet...")
        result = fb_client.REACTION("LIKE", object_id)

    # Xử lý kết quả trả về từ FB_API
    if result.get('success'):
        print(f"    ✓ Thanh cong tren Facebook!")
        return True
    else:
        err_msg = result.get('error', 'Loi khong ro')
        print(f"    ✗ That bai tren Facebook: {err_msg}")
        return False


def main(auth_token=None):
    global FB_ID, USERS_FB_ACCOUNT_ID, PARAMS, HEADERS
    
    print("==================================================")
    print("   BOT GOLIKE FB WEB API AUTOMATION (NO ADB)")
    print("==================================================")

    # Nhập / tải token Golike
    if auth_token:
        user_token = auth_token
    else:
        user_token = configure_token()
        if not user_token:
            return

    # Thử parse JSON cho các header g-auth và g-device-id
    try:
        data = json.loads(user_token)
        if isinstance(data, dict):
            HEADERS['authorization'] = data.get("authorization")
            if data.get("g-auth"):
                HEADERS['g-auth'] = data.get("g-auth")
            if data.get("g-device-id"):
                HEADERS['g-device-id'] = data.get("g-device-id")
    except Exception:
        if not user_token.startswith("Bearer "):
            user_token = f"Bearer {user_token}"
        HEADERS['authorization'] = user_token

    # Lấy tài khoản trên Golike
    print("\nDang lay danh sach tai khoan Facebook tu Golike...")
    golike_accounts = get_facebook_accounts()
    if not golike_accounts:
        print("Khong lay duoc danh sach tai khoan! Vui long kiem tra lai Token.")
        return

    # Lựa chọn phương thức nhập cookie
    print("\n--- CAU HINH COOKIE FACEBOOK ---")
    print("[1] Lay tu file single_mode_accounts.json (Chon tài khoan tu danh sach)")
    print("[2] Nhap truc tiep Cookie Facebook bang tay (Tự dong nhan dien)")
    method = input("Chon phuong thuc (mac dinh 1): ").strip()

    cookie = ""
    if method == "2":
        user_cookie = input("Nhap Cookie Facebook cua ban: ").strip()
        if not user_cookie:
            print("Cookie khong duoc de trong!")
            return
        cookie = user_cookie
        
        import re
        fb_uid = None
        match = re.search(r'c_user=(\d+)', user_cookie)
        if match:
            fb_uid = match.group(1)
            
        selected_acc = None
        for acc in golike_accounts:
            if acc.get('fb_id') == fb_uid:
                selected_acc = acc
                break
                
        if selected_acc:
            FB_ID = selected_acc['fb_id']
            USERS_FB_ACCOUNT_ID = selected_acc['id']
            print(f"=> Khop tai khoan Golike: {selected_acc.get('fb_name')} ({FB_ID}) - ID Golike: {USERS_FB_ACCOUNT_ID}")
        else:
            print("\n⚠️ Khong tim thay tai khoan Golike khop voi Cookie vua nhap.")
            print("Vui long chon tai khoan Golike tuong ung tu danh sach duoi day:")
            active_accounts = []
            idx = 1
            for acc in golike_accounts:
                print(f"[{idx}] {acc.get('fb_name')} ({acc.get('fb_id')})")
                active_accounts.append(acc)
                idx += 1
            try:
                choice = input("\nChon so thu tu tai khoan Golike cua cookie nay (mac dinh 1): ").strip()
                choice_idx = int(choice) - 1 if choice else 0
                if choice_idx < 0 or choice_idx >= len(active_accounts):
                    choice_idx = 0
            except ValueError:
                choice_idx = 0
            selected_acc = active_accounts[choice_idx]
            FB_ID = selected_acc['fb_id']
            USERS_FB_ACCOUNT_ID = selected_acc['id']
            print(f"=> Da chon tai khoan Golike: {selected_acc.get('fb_name')} ({FB_ID})")

        PARAMS['fb_id'] = FB_ID

        # Tự động cập nhật hoặc lưu vào single_mode_accounts.json
        try:
            filename = "single_mode_accounts.json"
            local_accounts = load_local_accounts()
            local_accounts = [acc for acc in local_accounts if acc.get('golike_uid') != FB_ID]
            new_acc = {
                "profile_name": selected_acc.get('fb_name'),
                "cookie": user_cookie,
                "golike_uid": FB_ID,
                "facebook_uid": fb_uid or FB_ID
            }
            local_accounts.append(new_acc)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"accounts": local_accounts}, f, indent=4, ensure_ascii=False)
            print("-> Da luu/cap nhat Cookie vao file single_mode_accounts.json.")
        except Exception as e:
            print(f"Loi khi luu cookie vao file JSON: {e}")
            
    else:
        # Load cookie cục bộ để đối chiếu
        local_accounts = load_local_accounts()
        cookie_map = {acc['golike_uid']: acc['cookie'] for acc in local_accounts if 'golike_uid' in acc}

        print("\n--- DANH SACH TAI KHOAN FACEBOOK ---")
        active_accounts = []
        idx = 1
        for acc in golike_accounts:
            fb_uid_temp = acc.get('fb_id')
            has_cookie = "Co Cookie" if fb_uid_temp in cookie_map else "Thieu Cookie"
            status_str = "Hoat dong" if acc.get('status') == 1 else "Khoa/Cho duyet"
            print(f"[{idx}] {acc.get('fb_name')} ({fb_uid_temp}) - {has_cookie} - Trang thai: {status_str}")
            active_accounts.append(acc)
            idx += 1

        try:
            choice = input("\nChon so thu tu tai khoan muon chay (mac dinh 1): ").strip()
            choice_idx = int(choice) - 1 if choice else 0
            if choice_idx < 0 or choice_idx >= len(active_accounts):
                choice_idx = 0
        except ValueError:
            choice_idx = 0

        selected_acc = active_accounts[choice_idx]
        FB_ID = selected_acc['fb_id']
        USERS_FB_ACCOUNT_ID = selected_acc['id']
        PARAMS['fb_id'] = FB_ID

        print(f"\n=> Chon tai khoan: {selected_acc.get('fb_name')} ({FB_ID})")

        # Kiểm tra Cookie của tài khoản được chọn
        if FB_ID not in cookie_map:
            print(f"⚠️ Khong tim thay Cookie cho tai khoan {selected_acc.get('fb_name')} ({FB_ID}) trong file single_mode_accounts.json!")
            user_cookie = input("Vui long nhap Cookie Facebook cho tai khoan nay: ").strip()
            if not user_cookie:
                print("❌ Khong co Cookie, dung hoat dong!")
                return
            cookie = user_cookie
            
            # Lưu cookie mới vào file single_mode_accounts.json để lần sau không cần nhập lại
            try:
                filename = "single_mode_accounts.json"
                new_acc = {
                    "profile_name": selected_acc.get('fb_name'),
                    "cookie": user_cookie,
                    "golike_uid": FB_ID,
                    "facebook_uid": FB_ID
                }
                local_accounts.append(new_acc)
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({"accounts": local_accounts}, f, indent=4, ensure_ascii=False)
                print("-> Da luu Cookie moi vao file single_mode_accounts.json.")
            except Exception as e:
                print(f"Loi khi luu cookie vao file JSON: {e}")
        else:
            cookie = cookie_map[FB_ID]


    print("🔄 Khoi tao phien lam viec Facebook...")
    fb_client = FB_API(cookie)
    login_status = fb_client.login()
    if isinstance(login_status, dict) and 'err' in login_status:
        print(f"❌ Loi dang nhap Facebook: {login_status['err']}")
        return
        
    print(f"✅ Dang nhap Facebook thanh cong! Actor ID (cookie): {fb_client.session.user_id}")
    
    # Ghi đè actor ID nếu Golike dùng profile phụ (i_user)
    if fb_client.session.user_id != FB_ID:
        print(f"⚠️ Phat hien sai lech UID! Dang switch Actor ID sang profile Golike: {FB_ID}")
        fb_client.set_actor_id(FB_ID)
    # Cấu hình delay trước khi chạy
    configure_delays()

    try:
        from ui.console import update_stats
        update_stats(selected_acc.get('fb_name', 'N/A'), FB_ID, 0, 0)
    except Exception:
        pass

    print("\nBat dau chay bot tu dong lam nhiem vu...")
    print(f"Delay Config: Action={DELAY_CONFIG['action_min']}-{DELAY_CONFIG['action_max']}s | "
          f"Report={DELAY_CONFIG['report_min']}-{DELAY_CONFIG['report_max']}s | "
          f"Jobs={DELAY_CONFIG['between_jobs_min']}-{DELAY_CONFIG['between_jobs_max']}s | "
          f"NoJob={DELAY_CONFIG['no_job_min']}-{DELAY_CONFIG['no_job_max']}s\n")

    job_count = 0
    success_count = 0
    fail_count = 0

    while True:
        print("=== Dang goi API lay danh sach Job moi ===")
        jobs = get_jobs()
        
        if jobs:
            print(f"Nhan duoc {len(jobs)} jobs moi. Bat dau xu ly tuan tu...")
            for index, job in enumerate(jobs, 1):
                job_count += 1
                print(f"\n[Job {index}/{len(jobs)}] (Tong: {job_count} | OK: {success_count} | Fail: {fail_count})")
                
                # Thực hiện nhiệm vụ qua HTTP Web API
                success = execute_job_via_web(fb_client, job)
                
                # Delay ngẫu nhiên sau khi thực hiện action trên Facebook
                random_delay('action_min', 'action_max', '⏱️ Delay sau action:')

                if success:
                    # Delay trước khi báo cáo để tránh "báo cáo quá nhanh"
                    random_delay('report_min', 'report_max', '⏱️ Delay truoc bao cao:')
                    if report_job(job):
                        success_count += 1
                        try:
                            import ui.console
                            reward = job.get('fix_coin_job') or 35
                            ui.console.update_stats(selected_acc.get('fb_name', 'N/A'), FB_ID, success_count, ui.console.total_coins + reward)
                        except Exception:
                            pass
                    else:
                        fail_count += 1
                else:
                    print("    Bao cao bo qua/bao loi job...")
                    skip_job(job)
                    fail_count += 1
                
                # Delay giữa các job
                if index < len(jobs):  # Không delay sau job cuối cùng
                    random_delay('between_jobs_min', 'between_jobs_max', '💤 Nghi giua cac job:')
                
            print(f"\nDa hoan thanh {len(jobs)} job. Tong: {job_count} | OK: {success_count} | Fail: {fail_count}")
            print("Chuan bi lay dot tiep theo...")
            # Delay ngắn trước khi lấy batch mới
            random_delay('between_jobs_min', 'between_jobs_max', '💤 Nghi truoc khi lay batch moi:')
        else:
            random_delay('no_job_min', 'no_job_max', '😴 Khong co job, nghi:')

if __name__ == "__main__":
    main()
