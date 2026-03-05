import os
import sys
from pathlib import Path
from PIL import Image, ExifTags
import piexif

def get_image_metadata(image_path: Path) -> dict:
    """Read metadata from image and return as a dictionary."""
    metadata = {
        "EXIF": {},
        "IPTC": {},
        "XMP": {},
        "Basic": {}
    }
    
    try:
        with Image.open(image_path) as img:
            # Basic Info
            metadata["Basic"] = {
                "Format": img.format,
                "Mode": img.mode,
                "Size": f"{img.size[0]} x {img.size[1]}",
                "FileSize": f"{os.path.getsize(image_path) / 1024:.2f} KB"
            }
            
            # EXIF via Pillow
            exif_data = img._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    # Convert bytes to string for readability
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='ignore')
                        except:
                            value = f"<Binary Data: {len(value)} bytes>"
                    metadata["EXIF"][str(tag)] = str(value)
            
            # Raw EXIF via piexif for more details
            try:
                exif_dict = piexif.load(img.info.get("exif", b""))
                for ifd in ("0th", "Exif", "GPS", "1st"):
                    for tag_id in exif_dict[ifd]:
                        tag_name = piexif.TAGS[ifd][tag_id]["name"]
                        val = exif_dict[ifd][tag_id]
                        if isinstance(val, bytes):
                            try:
                                val = val.decode('utf-8', errors='ignore')
                            except:
                                val = f"<Binary Data: {len(val)} bytes>"
                        metadata["EXIF"][tag_name] = str(val)
            except Exception:
                pass
                
            # XMP (often stored in img.info)
            if "xmp" in img.info:
                metadata["XMP"]["RawXMP"] = "Available"
                
    except Exception as e:
        print(f"Error reading metadata: {e}")
        
    return metadata

def strip_metadata(image_path: Path, output_path: Path = None) -> bool:
    """Remove all metadata from the image and save as a new file or overwrite."""
    if output_path is None:
        output_path = image_path
        
    try:
        with Image.open(image_path) as img:
            # Create a new image object with the same data but no metadata
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)
            
            # Save without any extra info
            clean_img.save(output_path, format=img.format)
            return True
    except Exception as e:
        print(f"Error stripping metadata: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.exists():
            print(get_image_metadata(p))
