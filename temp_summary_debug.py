import customtkinter as ctk
from ui_dashboard import Dashboard

d = Dashboard()
d.withdraw()
d.open_class_action('Grade 4', 'Summary')
d.update_idletasks()
print('content', d.content_panel.winfo_width(), d.content_panel.winfo_height(), d.content_panel.winfo_geometry())
print('current', d.current_view.winfo_width(), d.current_view.winfo_height(), d.current_view.winfo_geometry())
print('current_children', [(type(ch).__name__, ch.pack_info()['side']) for ch in d.current_view.winfo_children()])
d.destroy()
