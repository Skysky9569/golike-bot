"""
Module quản lý tác vụ cho hệ thống GoLike
"""

import json
from typing import List, Dict

class TaskManager:
    """Module quản lý tác vụ"""

    def __init__(self):
        self.current_tasks = []

    def load_tasks(self, filepath: str = "tasks.json"):
        """Tải danh sách tác vụ từ file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            self.current_tasks = tasks
            return tasks
        except FileNotFoundError:
            print(f"Không tìm thấy file {filepath}")
            return []
        except Exception as e:
            print(f"Lỗi khi tải tác vụ: {e}")
            return []

    def save_tasks(self, filepath: str = "tasks.json"):
        """Lưu danh sách tác vụ vào file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_tasks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi khi lưu tác vụ: {e}")

    def add_task(self, task_data):
        """Thêm tác vụ mới"""
        self.current_tasks.append(task_data)

    def get_task_by_id(self, task_id: str):
        """Lấy thông tin tác vụ theo ID"""
        for task in self.current_tasks:
            if task.get('id') == task_id:
                return task
        return None

    def get_all_tasks(self):
        """Lấy tất cả tác vụ"""
        return self.current_tasks

    def remove_task(self, task_id: str):
        """Xóa tác vụ"""
        self.current_tasks = [task for task in self.current_tasks if task.get('id') != task_id]