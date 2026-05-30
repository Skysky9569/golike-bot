"""
Job processors module for Golike application
Cung cap cac processor de xu ly jobs: ADB, Termux, Manual, U2.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from .adb_manager import ADBManager
from .logging import logger


class Job:
    """Represent mot job"""

    def __init__(self, job_id: str, link: str, job_type: str, object_id: str):
        """Khoi tao Job

        Args:
            job_id: ID cua job
            link: Link TikTok
            job_type: Loai job (like/follow)
            object_id: ID object
        """
        self.job_id = job_id
        self.link = link
        self.job_type = job_type
        self.object_id = object_id

    def __repr__(self) -> str:
        return f"Job(id={self.job_id}, type={self.job_type})"


class JobProcessor(ABC):
    """Base class cho job processor"""

    @abstractmethod
    def process(self, job: Job) -> bool:
        """Xu ly job

        Args:
            job: Job can xu ly

        Returns:
            bool: True neu thanh cong, False neu khong
        """
        pass


class ADBJobProcessor(JobProcessor):
    """Job processor su dung ADB"""

    def __init__(self, adb_manager: ADBManager, device_id: Optional[str] = None):
        """Khoi tao ADBJobProcessor

        Args:
            adb_manager: ADBManager instance
            device_id: ID thiet bi (neu None dung thiet bi mac dinh)
        """
        self.adb_manager = adb_manager
        self.device_id = device_id

    def process(self, job: Job) -> bool:
        """Xu ly job bang ADB

        Args:
            job: Job can xu ly

        Returns:
            bool: True neu thanh cong, False neu khong
        """
        return self.adb_manager.open_link(job.link, self.device_id)


class TermuxJobProcessor(JobProcessor):
    """Job processor su dung Termux"""

    def process(self, job: Job) -> bool:
        """Xu ly job bang Termux

        Args:
            job: Job can xu ly

        Returns:
            bool: True neu thanh cong, False neu khong
        """
        import os
        try:
            code = os.system(f"termux-open-url {job.link}")
            return code == 0
        except Exception:
            return False


class ManualJobProcessor(JobProcessor):
    """Job processor manual (hien thi link)"""

    def process(self, job: Job) -> bool:
        """Xu ly job manual

        Args:
            job: Job can xu ly

        Returns:
            bool: Luon tra ve True (user tu mo)
        """
        print(f"🔗 Link: {job.link}")
        print("   Vui long mo thu cong...")
        return True


class U2JobProcessor(JobProcessor):
    """Job processor dung uiautomator2 de mo link (khong can ADB truc tiep)"""

    def __init__(self, device_id: str):
        """Khoi tao U2JobProcessor

        Args:
            device_id: Dia chi IP:Port cua thiet bi (vd: 192.168.1.10:5555)
        """
        self.device_id = device_id
        self._u2_device = None

    def _get_device(self):
        """Lay ket noi uiautomator2 (cache lai tranh ket noi lai moi lan)"""
        if self._u2_device is None:
            try:
                import uiautomator2 as u2
                if self.device_id and ("." in self.device_id or ":" in self.device_id):
                    try:
                        import subprocess
                        from golike_core.adb_manager import ADBManager
                        adb_mgr = ADBManager()
                        adb_path = adb_mgr.adb_path
                        subprocess.run([adb_path, "connect", self.device_id], capture_output=True, timeout=5)
                    except Exception:
                        pass
                self._u2_device = u2.connect(self.device_id)
            except Exception as e:
                logger.error(f"Loi ket noi u2 de mo link: {e}")
        return self._u2_device

    def process(self, job: Job) -> bool:
        """Mo link tren thiet bi bang uiautomator2 shell

        Args:
            job: Job can xu ly

        Returns:
            bool: True neu thanh cong, False neu khong
        """
        try:
            device = self._get_device()
            if device is None:
                logger.error("Khong co ket noi u2 de mo link")
                return False
            result = device.shell(
                f'am start -a android.intent.action.VIEW -d "{job.link}"'
            )
            logger.info(f"u2 shell mo link: {result}")
            return True
        except Exception as e:
            logger.error(f"Loi mo link qua u2 shell: {e}")
            return False


def _call_process_job(ui_automator, job_type: str):
    """Wrapper tuong thich nguoc cho process_job().

    Ho tro ca tiktok_automation.py cu (tra 2-tuple) lan moi (3-tuple).

    Returns:
        Tuple[bool, str, bool]: (success, message, not_found)
    """
    result = ui_automator.process_job(job_type)
    if len(result) == 3:
        return result
    success, message = result
    not_found = "khong tim thay" in message.lower() or "khong tim thay" in message.lower()
    return success, message, not_found


class JobProcessorFactory:
    """Factory de tao job processor"""

    @staticmethod
    def create(method: str, adb_manager: Optional[ADBManager] = None, device_id: Optional[str] = None) -> JobProcessor:
        """Tao job processor

        Args:
            method: Phuong thuc (adb/termux/manual/u2/search)
            adb_manager: ADBManager instance (can cho adb)
            device_id: ID thiet bi (can cho adb/u2)

        Returns:
            JobProcessor: Job processor instance

        Raises:
            ValueError: Neu method khong hop le
        """
        if method == "adb":
            if not adb_manager:
                raise ValueError("ADBManager required for ADB method")
            return ADBJobProcessor(adb_manager, device_id)
        elif method == "termux":
            return TermuxJobProcessor()
        elif method == "u2":
            if not device_id:
                raise ValueError("device_id (IP:Port) required for u2 method")
            return U2JobProcessor(device_id)
        elif method == "manual":
            return ManualJobProcessor()
        elif method == "search":
            return ADBJobProcessor(adb_manager=adb_manager, device_id=device_id)
        else:
            raise ValueError(f"Unknown method: {method}")