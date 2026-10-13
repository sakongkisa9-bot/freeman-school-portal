from ui_dashboard import FreemanDB
db = FreemanDB()
print("License Record:", db.get_license_status())