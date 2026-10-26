from pathlib import Path
from typing import Any
from PIL import Image, ExifTags

def _convert_dms_to_decimal(dms_values: Any, ref: str) -> float | None:
    """
    Convert GPS Degrees, Minutes, Seconds tuple/list to Decimal Degrees.
    Format is typically ((degrees, 1), (minutes, 1), (seconds, 100)) or floats.
    """
    try:
        def to_float(val: Any) -> float:
            if hasattr(val, "numerator") and hasattr(val, "denominator"):
                return float(val.numerator) / float(val.denominator) if val.denominator != 0 else 0.0
            if isinstance(val, (tuple, list)) and len(val) == 2:
                return float(val[0]) / float(val[1]) if val[1] != 0 else 0.0
            return float(val)

        d = to_float(dms_values[0])
        m = to_float(dms_values[1])
        s = to_float(dms_values[2])

        decimal = d + (m / 60.0) + (s / 3600.0)
        if ref.upper() in ["S", "W"]:
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None

def extract_metadata(file_path: Path) -> dict[str, Any]:
    """
    Extracts real EXIF and container metadata from an image file.
    Does NOT invent or fabricate any fields.
    """
    result: dict[str, Any] = {
        "has_exif": False,
        "make": None,
        "model": None,
        "datetime_original": None,
        "datetime_digitized": None,
        "software": None,
        "gps_lat": None,
        "gps_lon": None,
        "gps_altitude": None,
        "image_format": None,
        "color_mode": None,
        "dimensions": None,
        "raw_tags": {},
        "notes": "",
    }

    try:
        with Image.open(file_path) as img:
            result["image_format"] = img.format
            result["color_mode"] = img.mode
            result["dimensions"] = {"width": img.width, "height": img.height}

            # Extract JPEG Quantization Tables (DQT) even if EXIF is stripped
            if hasattr(img, "quantization") and img.quantization:
                q_tables = {}
                for k, v in img.quantization.items():
                    q_tables[f"table_{k}"] = list(v) if hasattr(v, "__iter__") else v
                table_0 = q_tables.get("table_0", [])
                
                # Estimate JPEG quality from luminance DC/low-frequency quantization
                est_q = 75
                if table_0:
                    dc = table_0[0]
                    if dc <= 1:
                        est_q = 100
                    elif dc == 2:
                        est_q = 95
                    elif dc == 3:
                        est_q = 90
                    elif dc <= 5:
                        est_q = 85
                    elif dc <= 8:
                        est_q = 75
                    elif dc <= 12:
                        est_q = 65
                    elif dc <= 16:
                        est_q = 50
                    elif dc <= 32:
                        est_q = 30
                    else:
                        est_q = 15

                result["quantization_tables"] = {
                    "tables_present": list(q_tables.keys()),
                    "table_0_luminance_sample": table_0[:8],
                    "estimated_quality": est_q,
                }

            exif_data = img._getexif() if hasattr(img, "_getexif") else None
            
            if not exif_data:
                # Check for standard getexif() in newer Pillow versions
                if hasattr(img, "getexif"):
                    exif_obj = img.getexif()
                    if exif_obj and len(exif_obj) > 0:
                        exif_data = dict(exif_obj)

            if not exif_data:
                result["notes"] = "No EXIF metadata block found in image container."
                return result

            result["has_exif"] = True
            raw_parsed = {}
            gps_info = {}

            for tag_id, value in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                
                # Filter out huge binary blobs (like embedded thumbnails) for cleaner JSON
                if isinstance(value, bytes):
                    if len(value) > 64:
                        value_repr = f"<binary blob: {len(value)} bytes>"
                    else:
                        try:
                            value_repr = value.decode("utf-8", errors="ignore").strip()
                        except Exception:
                            value_repr = str(value)
                else:
                    value_repr = str(value)

                raw_parsed[tag_name] = value_repr

                # Extract specific standard tags
                if tag_name == "Make":
                    result["make"] = str(value).strip()
                elif tag_name == "Model":
                    result["model"] = str(value).strip()
                elif tag_name == "DateTimeOriginal":
                    result["datetime_original"] = str(value).strip()
                elif tag_name == "DateTimeDigitized":
                    result["datetime_digitized"] = str(value).strip()
                elif tag_name == "Software":
                    result["software"] = str(value).strip()
                elif tag_name == "GPSInfo" and isinstance(value, dict):
                    gps_info = value

            # Parse GPS data if available
            if gps_info:
                lat_dms = gps_info.get(2)  # GPSLatitude
                lat_ref = gps_info.get(1, "N")  # GPSLatitudeRef
                lon_dms = gps_info.get(4)  # GPSLongitude
                lon_ref = gps_info.get(3, "E")  # GPSLongitudeRef
                alt = gps_info.get(6)  # GPSAltitude

                if lat_dms:
                    result["gps_lat"] = _convert_dms_to_decimal(lat_dms, lat_ref)
                if lon_dms:
                    result["gps_lon"] = _convert_dms_to_decimal(lon_dms, lon_ref)
                if alt:
                    try:
                        if hasattr(alt, "numerator") and hasattr(alt, "denominator"):
                            result["gps_altitude"] = round(float(alt.numerator) / float(alt.denominator), 2)
                        else:
                            result["gps_altitude"] = round(float(alt), 2)
                    except Exception:
                        pass

            result["raw_tags"] = raw_parsed
            result["notes"] = f"Successfully parsed {len(raw_parsed)} metadata tags."
            return result

    except Exception as e:
        result["notes"] = f"Error during metadata extraction: {str(e)}"
        return result
