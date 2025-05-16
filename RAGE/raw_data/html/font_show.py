import tkinter as tk

def show_text_on_screen(text="Hello, World!"):
    root = tk.Tk()
    root.overrideredirect(True)  # 隐藏窗口边框
    root.attributes("-topmost", True)  # 保持窗口置顶
    root.geometry("+500+300")  # 设置窗口位置 (x=500, y=300)

    label = tk.Label(root, text=text, font=("Arial", 24), bg="white", fg="black")
    label.pack()

    # 点击窗口时关闭
    label.bind("<Button-1>", lambda e: root.destroy())

    root.mainloop()

show_text_on_screen("这是一个悬浮文本")
