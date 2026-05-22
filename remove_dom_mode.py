import os

def modify_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update version
    # It currently says: CURRENT_VERSION = "1.8.5"
    import re
    content = re.sub(
        r'CURRENT_VERSION = "1\.8\.5".*',
        r'CURRENT_VERSION = "1.8.6" # v1.8.6: Fast Switch mode, Server lock, Anti-spam loader-new fixes, removed DOM mode',
        content
    )
    
    # Wait, in the Git commit it might be "1.1.0" if I changed it?
    # Actually I didn't change CURRENT_VERSION when I committed! I only changed the CHANGELOG.md!
    # Let's handle both.
    content = re.sub(
        r'CURRENT_VERSION = "1\.1\.0".*',
        r'CURRENT_VERSION = "1.8.6" # v1.8.6: Fast Switch mode, Server lock, Anti-spam loader-new fixes, removed DOM mode',
        content
    )

    # 2. Remove DOM Functions
    start_str = "def run_selenium_dom_single():"
    end_str = "# ======================================================================\n# ==================== MENU KHỞI CHẠY HỆ THỐNG CHÍNH ==================\n# ======================================================================"
    
    start_idx = content.find(start_str)
    end_idx = content.find(end_str)
    
    if start_idx != -1 and end_idx != -1:
        # Keep everything before start_idx, and everything from end_idx onwards
        content = content[:start_idx] + content[end_idx:]
    else:
        print("Could not find DOM functions block")

    # 3. Update Menu text
    content = content.replace('print("4. 🆕 Chạy ĐƠN LẺ - Selenium DOM (click truc tiep Facebook)")\n', '')
    content = content.replace('        print("5. 🆕 Chạy SONG SONG - Selenium DOM (click truc tiep Facebook)")\n', '')
    content = content.replace('lua_chon = input("👉 Lựa chọn (1/2/3/4/5/0): ")', 'lua_chon = input("👉 Lựa chọn (1/2/3/0): ")')

    # 4. Remove menu logic
    menu_logic_old = '''            elif lua_chon == "4":
                run_selenium_dom_single()
            elif lua_chon == "5":
                run_selenium_dom_parallel()'''
    content = content.replace(menu_logic_old, '')

    # 5. Remove import
    content = content.replace('from fb_web_api import SeleniumDOMBot\n', '')
    content = content.replace('# Import Selenium DOM bot (che do moi - tương tác trực tiếp Facebook)\n', '')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Done")

if __name__ == "__main__":
    modify_file("golikefb_sele.py")
