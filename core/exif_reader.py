# core/exif_reader_qt.py
# 這是參考 exif_utils.py 邏輯重寫的、不依賴 Pillow 的純 Python 版本。
# 它使用多引擎策略來最大化讀取成功率。
#
# 請注意：此檔案需要安裝新的依賴函式庫。請在您的終端中執行：
# pip install piexif exifread

import os
import xml.etree.ElementTree as ET
import piexif
import exifread


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


def get_exif_data(image_path: str) -> dict:
    """
    綜合讀取 EXIF 和 XMP，採用不含 Pillow 的多引擎策略。
    策略順序: piexif -> XMP -> exifread
    """
    final_data = {}

    # --- 引擎 1: piexif (處理標準 JPEG/TIFF 的 EXIF) ---
    final_data.update(_read_exif_piexif(image_path))

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
