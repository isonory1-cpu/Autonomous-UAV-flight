import collections
import collections.abc
collections.MutableMapping = collections.abc.MutableMapping

import time
import tkinter as tk
from tkinter import messagebox, filedialog
from threading import Thread
from dronekit import connect, VehicleMode, LocationGlobalRelative

# Глобальная переменная для БПЛА
vehicle = None

# --- ФУНКЦИИ УПРАВЛЕНИЯ БПЛА ---

def connect_drone():
    """Подключение к дрону в отдельном потоке, чтобы GUI не зависал"""
    global vehicle
    connection_string = entry_connection.get()
    lbl_status.config(text="Подключение...", fg="orange")
    
    def target():
        global vehicle
        try:
            vehicle = connect(connection_string, wait_ready=False)
            lbl_status.config(text="ПОДКЛЮЧЕНО", fg="green")
            btn_takeoff.config(state=tk.NORMAL)
            btn_load_file.config(state=tk.NORMAL)
            btn_go_manual.config(state=tk.NORMAL)
            btn_rtl.config(state=tk.NORMAL)
            update_telemetry()
        except Exception as e:
            lbl_status.config(text="ОШИБКА СВЯЗИ", fg="red")
            messagebox.showerror("Ошибка", f"Не удалось подключиться: {e}")
            
    Thread(target=target, daemon=True).start()

def arm_and_takeoff():
    """Взлет дрона на заданную высоту"""
    try:
        alt = float(entry_alt_takeoff.get())
    except ValueError:
        messagebox.showerror("Ошибка", "Введите корректную высоту взлета")
        return

    def target():
        lbl_status.config(text="Взлет...", fg="orange")
        while not vehicle.is_armable:
            time.sleep(1)
        vehicle.mode = VehicleMode("GUIDED")
        vehicle.armed = True
        while not vehicle.armed:
            time.sleep(1)
        vehicle.simple_takeoff(alt)
        lbl_status.config(text="В полете (GUIDED)", fg="blue")

    Thread(target=target, daemon=True).start()

def send_to_coord(lat, lon, alt):
    """Отправка дрона в конкретную точку"""
    if vehicle:
        target_point = LocationGlobalRelative(lat, lon, alt)
        vehicle.simple_goto(target_point)
        print(f"Отправлена команда лететь к: {lat}, {lon}, {alt}")

def fly_manual():
    """Полет по координатам из полей ввода GUI"""
    try:
        lat = float(entry_lat.get())
        lon = float(entry_lon.get())
        alt = float(entry_alt.get())
        send_to_coord(lat, lon, alt)
    except ValueError:
        messagebox.showerror("Ошибка", "Заполните все поля координат числами!")

def fly_from_file():
    """Чтение файла и последовательный полет по точкам"""
    file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv")])
    if not file_path:
        return

    def target():
        try:
            with open(file_path, "r") as file:
                lines = file.readlines()

            lbl_status.config(text="Выполнение миссии из файла...", fg="purple")
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"): # Игнорируем пустые строки и комментарии
                    continue
                
                # Парсим координаты из строки
                lat_str, lon_str, alt_str = line.split(",")
                lat = float(lat_str.strip())
                lon = float(lon_str.strip())
                alt = float(alt_str.strip())
                
                # Отправляем дрон
                send_to_coord(lat, lon, alt)
                
                # Логика ожидания: ждем 10 секунд перед следующей точкой. 
                time.sleep(10)
                
            lbl_status.config(text="Миссия из файла завершена", fg="green")
            messagebox.showinfo("Миссия", "Все точки из файла пройдены!")
        except Exception as e:
            messagebox.showerror("Ошибка файла", f"Не удалось прочитать или исполнить файл:\n{e}")

    Thread(target=target, daemon=True).start()

def set_rtl():
    """Команда возврата домой"""
    if vehicle:
        vehicle.mode = VehicleMode("RTL")
        lbl_status.config(text="Возврат домой (RTL)", fg="red")

def update_telemetry():
    """Обновление данных о дроне на экране раз в секунду"""
    if vehicle:
        try:
            lat = vehicle.location.global_relative_frame.lat
            lon = vehicle.location.global_relative_frame.lon
            alt = vehicle.location.global_relative_frame.alt
            lbl_telemetry.config(text=f"Текущие координаты:\nШирота: {lat:.6f}\nДолгота: {lon:.6f}\nВысота: {alt:.1f} м")
        except:
            pass
    root.after(1000, update_telemetry)


# --- ГРАФИЧЕСКИЙ ИНТЕРФЕЙС (GUI) ---

root = tk.Tk()
root.title("Панель управления БПЛА автономного полета")
root.geometry("450x500")
root.resizable(False, False)

# Блок подключения
frame_conn = tk.LabelFrame(root, text=" 1. Подключение к БПЛА ")
frame_conn.pack(fill="x", padx=10, pady=5, ipady=5, ipadx=5)

tk.Label(frame_conn, text="Строка связи:").pack(side="left")
entry_connection = tk.Entry(frame_conn, width=20)
entry_connection.insert(0, "127.0.0.1:14550")
entry_connection.pack(side="left", padx=5)

btn_connect = tk.Button(frame_conn, text="Подключить", command=connect_drone)
btn_connect.pack(side="right")

# Блок статуса и телеметрии
frame_status = tk.LabelFrame(root, text=" Статус и Данные ")
frame_status.pack(fill="x", padx=10, pady=5, ipady=5, ipadx=5)

lbl_status = tk.Label(frame_status, text="ОТКЛЮЧЕНО", font=("Arial", 12, "bold"), fg="red")
lbl_status.pack()

lbl_telemetry = tk.Label(frame_status, text="Текущие координаты:\nШирота: ---\nДолгота: ---\nВысота: --- м", justify="left")
lbl_telemetry.pack(pady=5)

# Блок взлета
frame_takeoff = tk.LabelFrame(root, text=" 2. Старт ")
frame_takeoff.pack(fill="x", padx=10, pady=5, ipady=5, ipadx=5)

tk.Label(frame_takeoff, text="Высота взлета (м):").pack(side="left")
entry_alt_takeoff = tk.Entry(frame_takeoff, width=5)
entry_alt_takeoff.insert(0, "5")
entry_alt_takeoff.pack(side="left", padx=5)

btn_takeoff = tk.Button(frame_takeoff, text="ВЗЛЕТ", bg="lightgreen", state=tk.DISABLED, command=arm_and_takeoff)
btn_takeoff.pack(side="right", fill="x", expand=True)

# Блок управления миссией
frame_mission = tk.LabelFrame(root, text=" 3. Управление полетом ")
frame_mission.pack(fill="both", expand=True, padx=10, pady=5, ipady=5, ipadx=5)

# Полет из файла
btn_load_file = tk.Button(frame_mission, text="📂 Загрузить маршрут из файла (.txt)", state=tk.DISABLED, command=fly_from_file)
btn_load_file.pack(fill="x", pady=5)

tk.Label(frame_mission, text="- ИЛИ ВВЕСТИ ВРУЧНУЮ -", fg="gray").pack(pady=5)

# Ручной ввод координат
frame_manual_inputs = tk.Frame(frame_mission)
frame_manual_inputs.pack()

tk.Label(frame_manual_inputs, text="Широта:").grid(row=0, column=0, padx=2)
entry_lat = tk.Entry(frame_manual_inputs, width=10)
entry_lat.grid(row=0, column=1, padx=5)

tk.Label(frame_manual_inputs, text="Долгота:").grid(row=0, column=2, padx=2)
entry_lon = tk.Entry(frame_manual_inputs, width=10)
entry_lon.grid(row=0, column=3, padx=5)

tk.Label(frame_manual_inputs, text="Высота:").grid(row=0, column=4, padx=2)
entry_alt = tk.Entry(frame_manual_inputs, width=5)
entry_alt.insert(0, "10")
entry_alt.grid(row=0, column=5, padx=5)

btn_go_manual = tk.Button(frame_mission, text="🚀 Отправить в точку", state=tk.DISABLED, command=fly_manual)
btn_go_manual.pack(fill="x", pady=5)

# Аварийная кнопка
btn_rtl = tk.Button(frame_mission, text="🏠 ВОЗВРАТ ДОМОЙ (RTL)", bg="red", fg="white", font=("Arial", 10, "bold"), state=tk.DISABLED, command=set_rtl)
btn_rtl.pack(fill="x", side="bottom", pady=5)

root.mainloop()
