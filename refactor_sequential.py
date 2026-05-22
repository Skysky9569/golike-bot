import re
import sys

def modify_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    start_idx = -1
    end_idx = -1

    for i, line in enumerate(lines):
        if 'tb = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CLASS_NAME, \'swal2-title\')))' in line:
            start_idx = i - 1 # The '        try:' line before it
            break

    if start_idx == -1:
        print("Could not find start index")
        return

    # Find the corresponding except Exception as e: for the outer try block
    # Outer try block is at line 813.
    # The end of the while loop block is around line 1099 (sleep(5)).
    for i in range(start_idx, len(lines)):
        if "sleep(5)  # Keep as error retry - not configurable" in lines[i]:
            end_idx = i
            break
            
    if end_idx == -1:
        print("Could not find end index")
        return

    print(f"Refactoring lines from {start_idx} to {end_idx}")

    # Indent the block
    for i in range(start_idx, end_idx + 1):
        lines[i] = "    " + lines[i]

    # Prepend the loop and setup code
    loop_code = """
        for acc_idx, acc_info in enumerate(accounts_list):
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
                sleep(2)
                dismiss_da_hieu_modal(driver)
                click_kiem_xu_navigation(driver)
                sleep(1)
                click_facebook_job_category(driver)
                sleep(3)
"""
    lines.insert(start_idx, loop_code)

    # Now we need to modify the account selection logic and the break logic.
    # It's easier to write the modified lines out as a string and replace them.
    file_content = "".join(lines)

    # 1. Update break condition for limits
    old_break = """                    if job_limit_reached(driver):
                            _send_job_limit_telegram(name_run, uid_run)
                            print("[⚠️] Đã đạt giới hạn 100 jobs/ngày. Nhấn Enter để quay lại menu chính.")
                            input()
                            break"""
    new_break = """                    if job_limit_reached(driver):
                            _send_job_limit_telegram(name_run, uid_run)
                            print("[⚠️] Đã đạt giới hạn 100 jobs/ngày.")
                            if acc_idx == len(accounts_list) - 1:
                                input("Nhấn Enter để quay lại menu chính.")
                            break"""
    
    file_content = file_content.replace(old_break, new_break)
    
    # 2. Update account selection
    old_selection = """                print("\\n--- CHỌN TÀI KHOẢN CÀY ---")
                for i, (acc, name, acc_id) in enumerate(valid_accounts, start=1):
                    print(f"{i}. {name} | UID: {acc_id}")
                
                chon_acc = int(input("👉 Nhập số để chọn nick chạy: "))
                selected_node, name_run, uid_run = valid_accounts[chon_acc-1]
                driver.execute_script("arguments[0].click();", selected_node)"""
                
    new_selection = """                print("\\n--- CHỌN TÀI KHOẢN CÀY ---")
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
                    
                selected_node, name_run, uid_run = valid_accounts[chon_acc-1]
                driver.execute_script("arguments[0].click();", selected_node)"""
                
    file_content = file_content.replace(old_selection, new_selection)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(file_content)
        
    print("Successfully refactored golikefb_sele.py")

if __name__ == "__main__":
    modify_file("golikefb_sele.py")
