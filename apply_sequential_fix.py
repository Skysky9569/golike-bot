import os, json, textwrap, re

def modify_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add setup_multi_accounts
    setup_func = '''
def setup_multi_accounts():
    import os, json
    file_path = "multi_accounts.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                accounts = json.load(f)
            if accounts and isinstance(accounts, list):
                print("\\n--- TÌM THẤY DANH SÁCH TÀI KHOẢN ĐÃ LƯU ---")
                for i, acc in enumerate(accounts, 1):
                    print(f"{i}. UID: {acc.get('uid', 'N/A')}")
                ans = input("Bạn có muốn chạy danh sách này không? (y/n): ").strip().lower()
                if ans in ['y', 'yes', '']:
                    return accounts
        except: pass
        
    print("\\n--- NHẬP DANH SÁCH TÀI KHOẢN MỚI ---")
    print("Nhấn Enter để trống tại phần nhập Cookie khi bạn muốn kết thúc.")
    accounts = []
    idx = 1
    while True:
        c = input(f"Nhập Cookie cho Acc {idx}: ").strip()
        if not c:
            break
        u = input(f"Nhập UID cho Acc {idx}: ").strip()
        accounts.append({"cookie": c, "uid": u})
        idx += 1
        
    if accounts:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(accounts, f, indent=4)
        except: pass
            
    return accounts

def run_single_mode():'''
    content = content.replace("def run_single_mode():", setup_func)

    # 2. Update run_single_mode header
    old_header = '''    global STOP_FLAG
    STOP_FLAG = False
    print("\\n🚀 Bắt đầu thiết lập chế độ Chạy đơn lẻ 1 tài khoản...")
    cookie_fb = load_cookie()'''
    
    new_header = '''    global STOP_FLAG
    STOP_FLAG = False
    print("\\n🚀 Bắt đầu thiết lập chế độ Chạy đơn lẻ...")
    is_seq = input("Bạn có muốn chạy lần lượt nhiều tài khoản (Sequential Single Mode)? (y/n): ").strip().lower()
    accounts_list = []
    if is_seq in ['y', 'yes']:
        accounts_list = setup_multi_accounts()
        if not accounts_list:
            print("❌ Không có tài khoản nào được nhập. Thoát.")
            return
    else:
        cookie_fb = load_cookie()
        accounts_list = [{"cookie": cookie_fb, "uid": None}]'''
    content = content.replace(old_header, new_header)

    # 3. Update Fb API init outside loop
    old_fb_init = '''    proxy_auth_ext = None
    Fb = None
    if cookie_fb:
        fb_proxies = proxy_info["requests_proxies"] if proxy_info else None
        Fb = FB_API(cookie_fb, proxies=fb_proxies)
        Fb.login()'''
        
    new_fb_init = '''    proxy_auth_ext = None
    Fb = None
    fb_proxies = proxy_info["requests_proxies"] if proxy_info else None'''
    content = content.replace(old_fb_init, new_fb_init)
    
    # Extract the block using regex to be insensitive to line endings
    match = re.search(r'(        try:\n            tb = WebDriverWait\(driver, 3\)\.until\(EC\.element_to_be_clickable\(\(By\.CLASS_NAME, \'swal2-title\'\)\)\).*?                    sleep\(5\)  # Keep as error retry - not configurable\n)', content, re.DOTALL)
    
    if not match:
        print("Could not find block with regex!")
        return
        
    block_to_indent = match.group(1)
    start_idx = match.start(1)
    end_idx = match.end(1)
    
    # 6. Make replacements INSIDE the block BEFORE indenting
    old_acc_sel = '''            print("\\n--- CHỌN TÀI KHOẢN CÀY ---")
            for i, (acc, name, acc_id) in enumerate(valid_accounts, start=1):
                print(f"{i}. {name} | UID: {acc_id}")
            
            chon_acc = int(input("👉 Nhập số để chọn nick chạy: "))
            selected_node, name_run, uid_run = valid_accounts[chon_acc-1]'''
            
    new_acc_sel = '''            print("\\n--- CHỌN TÀI KHOẢN CÀY ---")
            for i, (acc, name, acc_id) in enumerate(valid_accounts, start=1):
                print(f"{i}. {name} | UID: {acc_id}")
            
            if current_uid:
                chon_acc = None
                for i, (acc, name, acc_id) in enumerate(valid_accounts, start=1):
                    if str(current_uid).strip() == str(acc_id).strip():
                        chon_acc = i
                        break
                if not chon_acc:
                    print(f"❌ Không tìm thấy nick GoLike với UID: {current_uid}. Bỏ qua!")
                    continue
            else:
                chon_acc = int(input("👉 Nhập số để chọn nick chạy: "))
            
            selected_node, name_run, uid_run = valid_accounts[chon_acc-1]'''
    
    if old_acc_sel in block_to_indent:
        block_to_indent = block_to_indent.replace(old_acc_sel, new_acc_sel)
    else:
        print("old_acc_sel not found!")
        
    old_break = '''                if job_limit_reached(driver):
                    _send_job_limit_telegram(name_run, uid_run)
                    print("[⚠️] Đã đạt giới hạn 100 jobs/ngày. Nhấn Enter để quay lại menu chính.")
                    input()
                    break'''
                    
    new_break = '''                if job_limit_reached(driver):
                    _send_job_limit_telegram(name_run, uid_run)
                    print("[⚠️] Đã đạt giới hạn 100 jobs/ngày.")
                    if acc_idx == len(accounts_list) - 1:
                        input("Nhấn Enter để quay lại menu chính.")
                    break'''
    
    if old_break in block_to_indent:
        block_to_indent = block_to_indent.replace(old_break, new_break)
    else:
        # Check if the telegram uid version is not there yet (because we reverted!)
        old_break_no_uid = '''                if job_limit_reached(driver):
                    print("[⚠️] Đã đạt giới hạn 100 jobs/ngày. Quay lại menu chính.")
                    break'''
        if old_break_no_uid in block_to_indent:
            new_break_no_uid = '''                if job_limit_reached(driver):
                    try:
                        from telegram_notifier import notify_job_limit
                        bot_token = CONFIG_DELAY.get("telegram_bot_token", "")
                        chat_id = CONFIG_DELAY.get("telegram_chat_id", "")
                        if bot_token and chat_id:
                            notify_job_limit(bot_token, chat_id, name_run, uid_run)
                    except: pass
                    print("[⚠️] Đã đạt giới hạn 100 jobs/ngày.")
                    if acc_idx == len(accounts_list) - 1:
                        input("Nhấn Enter để quay lại menu chính.")
                    break'''
            block_to_indent = block_to_indent.replace(old_break_no_uid, new_break_no_uid)
        else:
            print("old_break not found!")
        
    # 7. Indent the block
    indented_block = textwrap.indent(block_to_indent, "    ")
    
    # 8. Create the outer loop header
    outer_loop = '''        for acc_idx, acc_info in enumerate(accounts_list):
            if STOP_FLAG: break
            
            current_cookie = acc_info.get("cookie")
            current_uid = acc_info.get("uid")
            
            if current_cookie:
                Fb = FB_API(current_cookie, proxies=fb_proxies)
                Fb.login()
            else:
                Fb = None
                
            if acc_idx > 0:
                print(f"\\n🔄 Chuyển sang tài khoản tiếp theo (UID: {current_uid})...")
                click_home_navigation(driver)
                from time import sleep
                sleep(2)
                try:
                    btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Đã hiểu')]")
                    driver.execute_script("arguments[0].click();", btn)
                    sleep(1)
                except: pass
                click_kiem_xu_navigation(driver)
                sleep(1)
                try:
                    fb_b = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[1]/div[2]/div[3]/div[1]/div')))
                    driver.execute_script("arguments[0].click();", fb_b)
                except: pass
                sleep(3)

'''
    # 9. Stitch it all together
    content = content[:start_idx] + outer_loop + indented_block + content[end_idx:]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Done")

if __name__ == "__main__":
    modify_file("golikefb_sele.py")
