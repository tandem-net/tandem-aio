import sys
sys.path.append("/home/wnusair/Nextcloud/Summer Project (lockheed martin rizz)/Tandem/tandem-aio/server")
from app.utils.toml_reader import parse_toml_string, extract_name

try:
    with open("/home/wnusair/Nextcloud/Projects/Tandem-v1/tandem.toml", "rb") as f:
        parsed = parse_toml_string(f)
        print("Parsed:", parsed)
        print("Name:", extract_name(parsed))
except Exception as e:
    print("Error:", repr(e))
