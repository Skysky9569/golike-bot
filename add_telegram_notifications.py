"""Add Telegram notification calls at all job_limit_reached locations."""
import re

# File path
FILE_PATH = "golikefb_sele.py"

# Read the file
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# Add helper function after imports if not already present
helper_function = '''
def _send_job_limit_telegram(p_name: str):
    """Send job limit notification via Telegram."""
    if not HAS_TELEGRAM:
        return
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        from telegram_notifier import notify_job_limit
        notify_job_limit(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, p_name, "N/A")
    except:
        pass
'''

# Check if helper function already exists
if 'def _send_job_limit_telegram(' not in content:
    # Find a good place to insert the helper function (after other helper functions)
    # Insert after the job_limit_reached function
    match = re.search(r'def job_limit_reached\(driver\):.*?(?=\ndef |\Z)', content, re.DOTALL)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + '\n' + helper_function + content[insert_pos:]
        print("Added helper function")
    else:
        print("Could not find job_limit_reached function")
else:
    print("Helper function already exists")

# Pattern 1: Line 936 area (single account, breaks out of loop)
# Find: if job_limit_reached(driver):\n{whitespace}print.*?giới hạn 100 jobs.*?\n{whitespace}input\(\)
pattern1 = r'(if job_limit_reached\(driver\):)\n(\s+)print\("\[⚠️\] Đã đạt giới hạn 100 jobs/ngày'
replacement1 = r'\1\n\2_send_job_limit_telegram(name_run)\n\2print("[⚠️] Đã đạt giới hạn 100 jobs/ngày'
content = re.sub(pattern1, replacement1, content, count=1)
print(f"Pattern 1 (line ~936): replaced {content.count('_send_job_limit_telegram(name_run)')} occurrence")

# Pattern 2: Line 1292 area (p_name, breaks without input())
pattern2 = r'(if job_limit_reached\(driver\):)\n(\s+)print\("\[⚠️\] Đã đạt giới hạn 100 jobs/ngày\. Quay lại menu chính\."\)'
replacement2 = r'\1\n\2_send_job_limit_telegram(p_name)\n\2print("[⚠️] Đã đạt giới hạn 100 jobs/ngày. Quay lại menu chính.")'
content = re.sub(pattern2, replacement2, content, count=1)
print(f"Pattern 2 (line ~1292): replaced")

# Pattern 3: Line 1818 area (rotating cookies, Unicode without accents)
pattern3 = r'(if job_limit_reached\(driver\):)\n(\s+)if rotate_mode and current_cookie_idx \+ 1 < len\(cookie_list\):'
replacement3 = r'\1\n\2_send_job_limit_telegram(p_name)\n\2if rotate_mode and current_cookie_idx + 1 < len(cookie_list):'
content = re.sub(pattern3, replacement3, content, count=1)
print(f"Pattern 3 (line ~1818): replaced")

# Pattern 4: Line 2188 area (p_name, same as pattern 2)
pattern4 = r'(if job_limit_reached\(driver\):)\n(\s+)print\("\[⚠️\] Đã đạt giới hạn 100 jobs/ngày\. Quay lại menu chính\."\)'
replacement4 = r'\1\n\2_send_job_limit_telegram(p_name)\n\2print("[⚠️] Đã đạt giới hạn 100 jobs/ngày. Quay lại menu chính.")'
content = re.sub(pattern4, replacement4, content, count=1)
print(f"Pattern 4 (line ~2188): replaced")

# Write back
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ Updated {FILE_PATH}")
print("Next steps: 1) Run setup_telegram.py to configure, 2) Test with python -c ...")
