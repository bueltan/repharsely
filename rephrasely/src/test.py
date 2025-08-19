import win32gui
import win32con
import time

def find_slack_window():
    # Buscar ventanas con "Slack" en el título
    def enum_handler(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Slack" in title:
                result.append(hwnd)

    hwnds = []
    win32gui.EnumWindows(enum_handler, hwnds)
    return hwnds[0] if hwnds else None

def slack_nudge(intensity=10, shakes=10, delay=0.02):
    hwnd = find_slack_window()
    if not hwnd:
        print("No se encontró la ventana de Slack.")
        return

    # Restaurar la ventana si está minimizada
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    # Traer al frente
    win32gui.SetForegroundWindow(hwnd)

    # Obtener posición
    rect = win32gui.GetWindowRect(hwnd)
    x, y = rect[0], rect[1]

    # Zumbido
    for _ in range(shakes):
        win32gui.SetWindowPos(hwnd, None, x + intensity, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        time.sleep(delay)
        win32gui.SetWindowPos(hwnd, None, x - intensity, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        time.sleep(delay)

    # Restaurar posición original
    win32gui.SetWindowPos(hwnd, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)

# Ejecutar
slack_nudge()
