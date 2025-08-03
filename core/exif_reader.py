# core/exif_reader_qt.py
import os
import xml.etree.ElementTree as ET

import exifread
import piexif
from PIL import Image


def _parse_xmp(xmp_str: bytes) -> dict:
    """
    從 XMP 字串中解析元數據，兼容 Adobe 軟體輸出。
    此函數直接來自您提供的 exif_utils.py。
    """
    cleaned_data = {}
    try:
        if isinstance(xmp_str, bytes):
            xmp_str = xmp_str.decode('utf-8', 'ignore')

        rdf_start = xmp_str.find('<rdf:RDF')
        rdf_end = xmp_str.find('</rdf:RDF>')
        if rdf_start == -1 or rdf_end == -1:
            return {}

        xml_content = xmp_str[rdf_start:rdf_end + len('</rdf:RDF>')]
        root = ET.fromstring(xml_content)

        namespaces = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'tiff': 'http://ns.adobe.com/tiff/1.0/',
            'exif': 'http://ns.adobe.com/exif/1.0/',
        }

        descriptions = root.findall('rdf:Description', namespaces)

        def find_tag_text(path):
            for desc in descriptions:
                tag = desc.find(path, namespaces)
                if tag is not None and tag.text:
                    return tag.text.strip()
            return None

        cleaned_data['Make'] = find_tag_text('tiff:Make')
        cleaned_data['Model'] = find_tag_text('tiff:Model')

        fnumber_str = find_tag_text('exif:FNumber')
        if fnumber_str and '/' in fnumber_str:
            try:
                num, den = map(float, fnumber_str.split('/'))
                if den != 0: cleaned_data['FNumber'] = f"{(num / den):.1f}"
            except:
                pass

        cleaned_data['ExposureTime'] = find_tag_text('exif:ExposureTime')

        focal_str = find_tag_text('exif:FocalLength')
        if focal_str and '/' in focal_str:
            try:
                num, den = map(int, focal_str.split('/'))
                if den != 0: cleaned_data['FocalLength'] = int(num / den)
            except:
                pass

        iso_tag = root.find('.//exif:ISOSpeedRatings/rdf:Seq/rdf:li', namespaces)
        if iso_tag is not None and iso_tag.text:
            cleaned_data['ISO'] = iso_tag.text

        return {k: v for k, v in cleaned_data.items() if v}

    except Exception:
        return {}


def _read_exif_piexif(image_path: str) -> dict:
    """使用 piexif 函式庫讀取標準 EXIF。"""
    data = {}
    try:
        exif_dict = piexif.load(image_path)

        def safe_decode(val):
            return val.decode('utf-8', 'ignore').strip('\x00') if isinstance(val, bytes) else str(val).strip()

        if piexif.ImageIFD.Make in exif_dict.get("0th", {}):
            data['Make'] = safe_decode(exif_dict["0th"][piexif.ImageIFD.Make])
        if piexif.ImageIFD.Model in exif_dict.get("0th", {}):
            data['Model'] = safe_decode(exif_dict["0th"][piexif.ImageIFD.Model])

        exif_ifd = exif_dict.get("Exif", {})
        if piexif.ExifIFD.FNumber in exif_ifd:
            num, den = exif_ifd[piexif.ExifIFD.FNumber]
            if den != 0: data['FNumber'] = f"{num / den:.1f}"
        if piexif.ExifIFD.FocalLength in exif_ifd:
            num, den = exif_ifd[piexif.ExifIFD.FocalLength]
            if den != 0: data['FocalLength'] = int(num / den)
        if piexif.ExifIFD.ISOSpeedRatings in exif_ifd:
            data['ISO'] = exif_ifd[piexif.ExifIFD.ISOSpeedRatings]
        if piexif.ExifIFD.ExposureTime in exif_ifd:
            num, den = exif_ifd[piexif.ExifIFD.ExposureTime]
            if num == 1 and den > 1:
                data['ExposureTime'] = f"1/{den}"
            elif den != 0:
                data['ExposureTime'] = f"{num / den:.4f}"

    except Exception:
        pass
    return data


def _read_exif_with_pillow_backend(image_path: str) -> dict:
    """
    使用 Pillow 作為後端，讀取並解析EXIF，返回一個扁平化的顯示用字典。
    此方法能正確處理 Sub-IFD 和 IFDRational 物件。
    """
    display_data = {}
    try:
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            if not exif_data:
                return {}

            def safe_decode(val):
                return val.decode('utf-8', 'ignore').strip('\x00') if isinstance(val, bytes) else str(val).strip()

            # 從主目錄(0th IFD)讀取基本資訊
            if piexif.ImageIFD.Make in exif_data:
                display_data['Make'] = safe_decode(exif_data[piexif.ImageIFD.Make])
            if piexif.ImageIFD.Model in exif_data:
                display_data['Model'] = safe_decode(exif_data[piexif.ImageIFD.Model])

            # 獲取 Exif 子目錄
            exif_ifd = exif_data.get_ifd(piexif.ImageIFD.ExifTag)

            # --- 從 Exif 子目錄中讀取詳細參數，並正確處理 IFDRational 物件 ---

            if piexif.ExifIFD.FNumber in exif_ifd:
                # 【修正】不再嘗試解包，而是直接訪問 IFDRational 物件的屬性
                rational_val = exif_ifd[piexif.ExifIFD.FNumber]
                if rational_val.denominator != 0:
                    display_data['FNumber'] = f"{rational_val.numerator / rational_val.denominator:.1f}"

            if piexif.ExifIFD.ExposureTime in exif_ifd:
                # 【修正】處理 ExposureTime 的 IFDRational 物件
                rational_val = exif_ifd[piexif.ExifIFD.ExposureTime]
                num, den = rational_val.numerator, rational_val.denominator
                if num == 1 and den > 1:
                    display_data['ExposureTime'] = f"1/{den}"
                elif den != 0:
                    display_data['ExposureTime'] = f"{num / den:.4f}".rstrip('0').rstrip('.')

            if piexif.ExifIFD.ISOSpeedRatings in exif_ifd:
                # ISO 通常是整數，不需要特殊處理
                display_data['ISO'] = str(exif_ifd[piexif.ExifIFD.ISOSpeedRatings])

            if piexif.ExifIFD.FocalLength in exif_ifd:
                # 【修正】處理 FocalLength 的 IFDRational 物件
                rational_val = exif_ifd[piexif.ExifIFD.FocalLength]
                if rational_val.denominator != 0:
                    display_data['FocalLength'] = str(int(rational_val.numerator / rational_val.denominator))

    except Exception as e:
        print(f"在 _read_exif_with_pillow_backend 中發生錯誤: {e}")
        pass

    return display_data


def debug_read_exif(image_path: str):
    """
    這是一個偵錯專用函式，用於徹底檢查 Pillow 讀取 EXIF 時的內部狀態。
    """
    print("\n" + "="*20 + f" 開始對 {os.path.basename(image_path)} 進行法醫式偵錯 " + "="*20)
    try:
        with Image.open(image_path) as img:
            # 偵錯點 1: 打印 Pillow 最底層的 .info 字典
            # 這裡可能直接包含名為 'exif' 的原始位元組
            print(f"\n[偵錯 1] img.info 內容:\n{img.info}\n")

            # 偵錯點 2: 嘗試獲取 Exif 物件並打印其類型
            exif_data = img.getexif()
            if not exif_data:
                print("[偵錯 2] img.getexif() 返回了 None 或空物件。偵錯結束。\n")
                return

            print(f"[偵錯 2] img.getexif() 返回的物件類型: {type(exif_data)}\n")

            # 偵錯點 3: 遍歷並打印 Exif 物件中的所有頂層標籤
            print("[偵錯 3] Exif 物件頂層目錄中的所有標籤 (key: value):")
            if hasattr(exif_data, 'items'):
                for key, value in exif_data.items():
                    # 為了避免打印超長位元組，對 value 做一下截斷
                    value_repr = repr(value)
                    if len(value_repr) > 100:
                        value_repr = value_repr[:100] + '...'
                    print(f"  - Key: {key}, Type: {type(key)}, Value: {value_repr}")
            else:
                print("  - 此物件不支援 .items() 遍歷。")
            print("-" * 40)

            # 偵錯點 4: 嘗試獲取 Exif 子目錄並打印
            print("\n[偵錯 4] 嘗試獲取 Exif 子目錄 (Sub-IFD):")
            try:
                exif_ifd = exif_data.get_ifd(piexif.ExifIFD.TAGS)
                print("  - 成功獲取 Exif 子目錄！")
                print(f"  - 子目錄類型: {type(exif_ifd)}")
                print(f"  - 子目錄內容:\n{exif_ifd}\n")
            except Exception as e:
                print(f"  - 獲取 Exif 子目錄時發生錯誤: {e}\n")

    except Exception as e:
        print(f"打開或處理圖片時發生了嚴重錯誤: {e}")

    print("="*25 + " 偵錯結束 " + "="*25 + "\n")
    # 為了讓原有的 get_exif_data 不報錯，我們返回一個空字典
    return {}

def _extract_xmp_from_file(image_path: str) -> bytes | None:
    """
    不依賴任何圖片函式庫，直接從二進位檔案流中搜尋並提取 XMP 數據區塊。
    """
    try:
        with open(image_path, 'rb') as f:
            # 讀取檔案的一部份進行搜尋，避免讀取超大檔案
            chunk = f.read(200 * 1024)  # 讀取前 200KB
        start_tag = b"<x:xmpmeta"
        end_tag = b"</x:xmpmeta>"
        start = chunk.find(start_tag)
        if start != -1:
            end = chunk.find(end_tag, start)
            if end != -1:
                return chunk[start: end + len(end_tag)]
    except Exception:
        pass
    return None


def reconstruct_exif_dict(flat_exif_data: dict) -> dict | None:
    """
    將扁平的、用於顯示的EXIF字典，重建為 piexif.dump() 所需的巢狀字典。
    """
    if not flat_exif_data:
        return None

    zeroth_ifd = {}
    exif_ifd = {}

    # --- 映射 '0th' IFD (Image File Directory) ---
    if flat_exif_data.get('Make'):
        zeroth_ifd[piexif.ImageIFD.Make] = str(flat_exif_data['Make']).encode('utf-8')
    if flat_exif_data.get('Model'):
        zeroth_ifd[piexif.ImageIFD.Model] = str(flat_exif_data['Model']).encode('utf-8')

    # --- 映射 'Exif' IFD ---
    if flat_exif_data.get('FNumber'):
        try:
            f_number = float(flat_exif_data['FNumber'])
            # 【修正】將 FNumber 正確地放入 exif_ifd 中
            exif_ifd[piexif.ExifIFD.FNumber] = (int(f_number * 100), 100)
        except ValueError:
            pass

    if flat_exif_data.get('ExposureTime'):
        exposure_str = str(flat_exif_data['ExposureTime'])
        try:
            if '/' in exposure_str:
                num, den = map(int, exposure_str.split('/'))
                exif_ifd[piexif.ExifIFD.ExposureTime] = (num, den)
            else:
                exposure_float = float(exposure_str)
                if exposure_float < 1:
                    exif_ifd[piexif.ExifIFD.ExposureTime] = (1, int(1 / exposure_float))
                else:
                    exif_ifd[piexif.ExifIFD.ExposureTime] = (int(exposure_float * 1000), 1000)
        except (ValueError, ZeroDivisionError):
            pass

    if flat_exif_data.get('ISO'):
        try:
            exif_ifd[piexif.ExifIFD.ISOSpeedRatings] = int(flat_exif_data['ISO'])
        except ValueError:
            pass

    if flat_exif_data.get('FocalLength'):
        try:
            focal_length = int(flat_exif_data['FocalLength'])
            exif_ifd[piexif.ExifIFD.FocalLength] = (focal_length, 1)
        except ValueError:
            pass

    if not zeroth_ifd and not exif_ifd:
        return None

    return {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": {}, "1st": {}, "thumbnail": None}


def get_exif_data(image_path: str) -> dict:
    """
    綜合讀取 EXIF 和 XMP，採用不含 Pillow 的多引擎策略。
    策略順序: piexif -> XMP -> exifread
    """
    final_data = {}

    # --- 引擎 1: piexif (處理標準 JPEG/TIFF 的 EXIF) ---
    final_data.update(_read_exif_with_pillow_backend(image_path))
    print(f"[DEBUG] final_data: {final_data}")

    # --- 引擎 2: 手動 XMP 解析 (處理後製軟體輸出的元數據) ---
    xmp_bytes = _extract_xmp_from_file(image_path)
    if xmp_bytes:
        xmp_data = _parse_xmp(xmp_bytes)
        # XMP 的數據通常更新、更權威，所以用它來覆蓋之前讀到的值
        final_data.update(xmp_data)

    # --- 引擎 3: exifread (作為最後的補充) ---
    # 如果核心資訊 (如相機型號) 仍然缺失，才啟用 exifread
    if 'Model' not in final_data:
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f, details=False, stop_tag='JPEGThumbnail')

            if 'Image Make' in tags and 'Make' not in final_data:
                final_data['Make'] = str(tags['Image Make']).strip()
            if 'Image Model' in tags and 'Model' not in final_data:
                final_data['Model'] = str(tags['Image Model']).strip()
        except Exception:
            pass

    print(f"Multi-engine EXIF Reader found: {final_data}")
    return final_data
