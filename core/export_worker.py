import os

import piexif
from PIL.ImageQt import fromqimage
from PyQt6.QtCore import pyqtSignal, QObject

from core.exif_reader import get_exif_data, reconstruct_exif_dict


class ExportWorker(QObject):
    """
    導出任務的工作線程。
    繼承自 QObject 以便使用信號/槽機制。
    """
    # 定義信號
    # 參數: 當前進度 (int), 總數 (int), 當前檔案名 (str)
    progress = pyqtSignal(int, int, str)
    # 參數: 錯誤訊息 (str)
    error = pyqtSignal(str)
    # 無參數
    finished = pyqtSignal()

    def __init__(self, selected_paths, output_dir, all_settings, render_function, parent=None):
        super().__init__(parent)
        self.selected_paths = selected_paths
        self.output_dir = output_dir
        self.all_settings = all_settings
        self._render_image_for_export = render_function  # 接收渲染函數
        self._is_cancelled = False

    def run_export(self):
        """
        執行導出的主方法。
        """
        total_count = len(self.selected_paths)
        try:
            for i, path in enumerate(self.selected_paths):
                if self._is_cancelled:
                    break

                # 發送信號來更新 UI
                self.progress.emit(i, total_count, f"{i} / {total_count} - {os.path.basename(path)}")

                # --- 核心處理邏輯 ---
                final_pixmap = self._render_image_for_export(path, self.all_settings)
                if not final_pixmap:
                    print(f"Warning: Rendering failed for {path}, skipping.")
                    continue

                flat_exif = get_exif_data(path)
                exif_dict_for_writing = reconstruct_exif_dict(flat_exif)

                base_name = os.path.basename(path)
                name, _ = os.path.splitext(base_name)
                output_filename = f"{name}_framed.png"
                output_path = os.path.join(self.output_dir, output_filename)

                qimage_to_save = final_pixmap.toImage()
                pil_image_to_save = fromqimage(qimage_to_save).convert("RGBA")

                save_args = {'compress_level': 6}
                if exif_dict_for_writing:
                    try:
                        exif_bytes = piexif.dump(exif_dict_for_writing)
                        save_args['exif'] = exif_bytes
                    except Exception as dump_error:
                        print(f"無法將EXIF字典轉換為位元組: {dump_error}")

                pil_image_to_save.save(output_path, **save_args)
                # --- 核心處理邏輯結束 ---

            if not self._is_cancelled:
                # 完成後更新最後一筆進度
                self.progress.emit(total_count, total_count, "Completed")

        except Exception as e:
            # 發送錯誤信號
            self.error.emit(str(e))
        finally:
            # 無論成功或失敗，最後都發送完成信號
            self.finished.emit()

    def cancel(self):
        """
        從外部調用的槽，用來設置取消標誌。
        """
        self._is_cancelled = True
