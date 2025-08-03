import os
import threading

import piexif
from PIL.ImageQt import fromqimage
from PyQt6.QtCore import pyqtSignal, QObject, QRunnable, QThreadPool

from core.exif_reader import get_exif_data, reconstruct_exif_dict


class RunnableSignals(QObject):
    """
    一個 QObject 子類別，專門用來為 QRunnable 提供信號。
    因為 QRunnable 本身不是 QObject，無法自定義信號。
    """
    progress = pyqtSignal(int, int, str)  # 當前進度, 總數, 訊息
    error = pyqtSignal(str, str)  # 錯誤訊息, 相關檔案路徑
    finished = pyqtSignal()  # 所有任務完成


class ImageExportTask(QRunnable):
    """
    代表一個獨立的圖片導出任務，將在執行緒池中運行。
    """

    def __init__(self, image_path, output_dir, all_settings, render_function, signals, progress_counter_ref,
                 progress_lock, total_count):
        super().__init__()
        # --- 任務所需資料 ---
        self.image_path = image_path
        self.output_dir = output_dir
        self.all_settings = all_settings
        self.render_function = render_function
        # --- 通訊與進度控制 ---
        self.signals = signals
        self.progress_counter = progress_counter_ref  # [int] 一個包含整數的列表，用作引用傳遞
        self.progress_lock = progress_lock  # threading.Lock 物件
        self.total_count = total_count

    def run(self):
        """QThreadPool 會自動調用此方法。"""
        try:
            final_pixmap = self.render_function(self.image_path, self.all_settings)
            if not final_pixmap:
                raise RuntimeError(f"渲染失敗 (Rendering failed for) {self.image_path}")

            flat_exif = get_exif_data(self.image_path)
            exif_dict_for_writing = reconstruct_exif_dict(flat_exif)

            base_name = os.path.basename(self.image_path)
            name, _ = os.path.splitext(base_name)
            output_filename = f"{name}_framed.png"
            output_path = os.path.join(self.output_dir, output_filename)

            qimage_to_save = final_pixmap.toImage()
            pil_image_to_save = fromqimage(qimage_to_save).convert("RGBA")

            save_args = {'compress_level': 6}
            if exif_dict_for_writing:
                exif_bytes = piexif.dump(exif_dict_for_writing)
                save_args['exif'] = exif_bytes

            pil_image_to_save.save(output_path, **save_args)

            with self.progress_lock:
                self.progress_counter[0] += 1
                current_progress = self.progress_counter[0]
            # 發送進度信號
            msg = f"{current_progress} / {self.total_count} - {os.path.basename(self.image_path)}"
            self.signals.progress.emit(current_progress, self.total_count, msg)

        except Exception as e:
            # 發送錯誤信號
            self.signals.error.emit(str(e), self.image_path)
        finally:
            # 再次獲取鎖來檢查最終計數
            with self.progress_lock:
                if self.progress_counter[0] == self.total_count:
                    self.signals.finished.emit()


class ExportManager(QObject):
    """
    管理 QThreadPool 並分發所有導出任務。
    這個物件將運行在主執行緒中，它的啟動是非阻塞的。
    """

    def __init__(self, selected_paths, output_dir, all_settings, render_function, parent=None):
        super().__init__(parent)
        self.selected_paths = selected_paths
        self.output_dir = output_dir
        self.all_settings = all_settings
        self.render_function = render_function
        self._was_cancelled = False  # <--- 新增旗標

        self.signals = RunnableSignals()
        # 使用全域的執行緒池
        self.pool = QThreadPool.globalInstance()
        # 使用一個普通的 Python 列表來模擬引用傳遞，並創建一個鎖
        self.progress_counter = [0]
        self.progress_lock = threading.Lock()

        # 根據 CPU 核心數設定最大執行緒數，-2 是為了保留核心給 UI 和系統
        cpu_cores = os.cpu_count() or 1
        self.pool.setMaxThreadCount(max(1, cpu_cores - 2))
        print(f"導出任務將使用最多 {self.pool.maxThreadCount()} 個執行緒。")

    def start(self):
        """開始將所有任務提交到執行緒池。"""
        total_count = len(self.selected_paths)
        if total_count == 0:
            self.signals.finished.emit()
            return

        for path in self.selected_paths:
            # 為每張圖片創建一個任務
            task = ImageExportTask(
                image_path=path,
                output_dir=self.output_dir,
                all_settings=self.all_settings,
                render_function=self.render_function,
                signals=self.signals,
                progress_counter_ref=self.progress_counter,  # 傳遞列表
                progress_lock=self.progress_lock,  # 傳遞鎖
                total_count=total_count
            )
            # 將任務提交給執行緒池，它會自動安排執行緒來運行 task.run()
            self.pool.start(task)

    def cancel(self):
        """取消尚未開始的任務。注意：無法停止已經在運行的任務。"""
        self._was_cancelled = True  # <--- 設置旗標
        self.pool.clear()
        self.signals.finished.emit()  # 強制觸發完成以進行清理

    def is_cancelled(self) -> bool:  # <--- 新增方法
        """回報任務是否被使用者手動取消。"""
        return self._was_cancelled
