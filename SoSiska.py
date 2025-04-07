import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageFilter, ImageDraw

class ImageProcessor:
    def __init__(self, master):
        self.master = master
        master.title("SoSiska v 0.2a")

        self.canvas_width = 650
        self.canvas_height = 650
        self.memory_limit = 5
        self.memory = []

        # Guide lines settings
        self.guide_line_offset = 10
        self.guide_lines_visible = True
        self.magnetic = False

        # Chat state flags
        self.chat_cropped = False
        self.chat_outlined = False
        self.magnetic_override = False  # Manual magnetic control

        # Undo/Redo history
        self.history = []
        self.history_index = -1

        # UI elements initialization
        self.setup_ui()

    def setup_ui(self):
        # Frame for buttons
        button_frame = tk.Frame(self.master)
        button_frame.pack(pady=5)

        self.load_bg_button = tk.Button(button_frame, text="Загрузить Фон", command=self.load_background)
        self.load_bg_button.pack(side=tk.LEFT, padx=5)

        self.load_chat_button = tk.Button(button_frame, text="Загрузить Чат", command=self.load_chat)
        self.load_chat_button.pack(side=tk.LEFT, padx=5)

        self.outline_button = tk.Button(button_frame, text="Добавить Обводку", command=self.add_outline)
        self.outline_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(button_frame, text="Сохранить", command=self.save_image)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.memory_button = tk.Button(button_frame, text="Сохранить в Память", command=self.save_to_memory)
        self.memory_button.pack(side=tk.LEFT, padx=5)

        self.process_memory_button = tk.Button(button_frame, text="Склеить и Сохранить", command=self.process_memory)
        self.process_memory_button.pack(side=tk.LEFT, padx=5)

        self.change_canvas_size_button = tk.Button(button_frame, text="Изменить Размер Холста", command=self.change_canvas_size)
        self.change_canvas_size_button.pack(side=tk.LEFT, padx=5)

        self.toggle_guide_lines_button = tk.Button(button_frame, text="Показать/Скрыть Направляющие", command=self.toggle_guide_lines)
        self.toggle_guide_lines_button.pack(side=tk.LEFT, padx=5)

        self.toggle_magnetic_button = tk.Button(button_frame, text="Включить Примагничивание", command=self.toggle_magnetic)
        self.toggle_magnetic_button.pack(side=tk.LEFT, padx=5)

        # Scale setup
        self.scale_var = tk.DoubleVar(value=1.0)
        self.scale = tk.Scale(button_frame, variable=self.scale_var, orient=tk.HORIZONTAL, from_=0.1, to=5.0, resolution=0.1, label="Масштаб", command=self.rescale_background)
        self.scale.pack(side=tk.LEFT, padx=5)

        # Canvas setup
        self.canvas = tk.Canvas(self.master, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas.pack()

        # Bindings for background image dragging
        self.canvas.bind("<ButtonPress-1>", self.start_move_bg)
        self.canvas.bind("<B1-Motion>", self.move_bg)
        self.canvas.bind("<ButtonRelease-1>", self.stop_move_bg)

        # Bindings for chat image dragging
        self.canvas.bind("<ButtonPress-3>", self.start_move_chat)
        self.canvas.bind("<B3-Motion>", self.move_chat)
        self.canvas.bind("<ButtonRelease-3>", self.stop_move_chat)

        # Bindings for selection tool
        self.canvas.bind("<ButtonPress-2>", self.start_selection)
        self.canvas.bind("<B2-Motion>", self.draw_selection)
        self.canvas.bind("<ButtonRelease-2>", self.end_selection)

        # Bindings for deletion tool
        self.canvas.bind("s", self.start_delete_selection)
        self.canvas.bind("<Control-z>", self.undo)
        self.canvas.bind("<Control-y>", self.redo)

        # Image data
        self.bg_image = None
        self.bg_image_tk = None
        self.bg_x = 0
        self.bg_y = 0
        self.moving_bg = False
        self.bg_rect_id = None # Id of the rectangle around bg image

        self.chat_image = None
        self.chat_image_tk = None
        self.chat_x = 0  # Start at top-left corner
        self.chat_y = 0  # Start at top-left corner
        self.moving_chat = False
        self.chat_rect_id = None # Id of the rectangle around chat image

        # Selection tool data
        self.rect_start_x = None
        self.rect_start_y = None
        self.rect_id = None
        self.selection_coords = None

        # Deletion tool data
        self.delete_rect_start_x = None
        self.delete_rect_start_y = None
        self.delete_rect_id = None
        self.delete_coords = None

        # Canvas outline
        self.canvas.create_rectangle(0, 0, self.canvas_width, self.canvas_height, outline="black")

        # Memory images indicator
        self.memory_indicator = tk.Label(self.master, text=f"В памяти: {len(self.memory)}/{self.memory_limit}")
        self.memory_indicator.pack()

        # Add tooltips
        self.add_tooltips()

        self.update_magnetic_button_state() # Initial magnetic button state

    def add_tooltips(self):
        tooltips = {
            self.load_bg_button: "Загружает фоновое изображение",
            self.load_chat_button: "Загружает изображение чата",
            self.outline_button: "Добавляет обводку к изображению чата",
            self.save_button: "Сохраняет изображение",
            self.memory_button: "Сохраняет текущий вид холста в память",
            self.process_memory_button: "Склеивает все изображения из памяти и сохраняет",
            self.change_canvas_size_button: "Изменяет размер холста",
            self.toggle_guide_lines_button: "Показывает или скрывает направляющие",
            self.toggle_magnetic_button: "Включает или выключает примагничивание",
        }

        for button, text in tooltips.items():
            button.bind("<Enter>", lambda event, t=text: self.show_tooltip(event, t))
            button.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event, text):
        # Create a tooltip window
        self.tooltip = tk.Toplevel(self.master)
        self.tooltip.overrideredirect(True)  # Remove window decorations
        self.tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")  # Position the tooltip

        # Add text to the tooltip
        label = tk.Label(self.tooltip, text=text, background="#FFFFE0", relief="solid", borderwidth=1, font=("arial", "8", "normal"))
        label.pack()

    def hide_tooltip(self, event):
        # Destroy the tooltip window
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()

    def load_background(self):
        filename = filedialog.askopenfilename(initialdir=".", title="Выберите фоновое изображение",
                                              filetypes=(("Изображения", "*.png;*.jpg;*.jpeg"), ("Все файлы", "*.*")))
        if filename:
            self.bg_image = Image.open(filename)
            self.bg_image_tk = ImageTk.PhotoImage(self.bg_image)
            self.rescale_background(self.scale_var.get())  # Изначальное масштабирование
            self.draw_images()
            self.save_state()

    def load_chat(self):
        filename = filedialog.askopenfilename(initialdir=".", title="Выберите изображение чата",
                                              filetypes=(("Изображения", "*.png;*.jpg;*.jpeg"), ("Все файлы", "*.*")))
        if filename:
            self.chat_image = Image.open(filename)
            self.remove_black_background()
            self.chat_x = 0 # Resetting coordinates for chat image
            self.chat_y = 0 # Resetting coordinates for chat image
            self.draw_chat()
            self.save_state()

    def remove_black_background(self, threshold=50):
        if self.chat_image:
            img = self.chat_image.convert("RGBA")
            data = img.getdata()
            new_data = []
            for item in data:
                if item[0] < threshold and item[1] < threshold and item[2] < threshold:
                    new_data.append((0, 0, 0, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            self.chat_image = img
            # Force rasterization of chat image
            self.chat_image = self.chat_image.copy()

    def draw_images(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, self.canvas_width, self.canvas_height, outline="black")  # Redraw outline

        if self.bg_image_tk:
            self.canvas.create_image(self.bg_x, self.bg_y, anchor=tk.NW, image=self.bg_image_tk)
            # Draw rectangle around background image
            if self.bg_image:
                width, height = self.bg_image.size
                x1, y1 = self.bg_x, self.bg_y
                x2, y2 = self.bg_x + width, self.bg_y + height
                if self.bg_rect_id:
                    self.canvas.delete(self.bg_rect_id)
                self.bg_rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline="blue")

        if self.chat_image_tk:
            self.canvas.create_image(self.chat_x, self.chat_y, anchor=tk.NW, image=self.chat_image_tk)
            # Draw rectangle around chat image
            if self.chat_image:
                width, height = self.chat_image.size
                x1, y1 = self.chat_x, self.chat_y
                x2, y2 = self.chat_x + width, self.chat_y + height
                if self.chat_rect_id:
                    self.canvas.delete(self.chat_rect_id)
                self.chat_rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline="green")

        self.draw_guide_lines()

    def draw_chat(self):
        self.chat_image_tk = ImageTk.PhotoImage(self.chat_image)
        self.draw_images()

    def start_move_bg(self, event):
        if self.bg_image:  # Check if background image is loaded
            self.moving_bg = True
            self.start_x = event.x - self.bg_x
            self.start_y = event.y - self.bg_y

    def move_bg(self, event):
        if self.moving_bg:
            self.bg_x = event.x - self.start_x
            self.bg_y = event.y - self.start_y
            self.draw_images()

    def stop_move_bg(self, event):
        self.moving_bg = False

    def start_move_chat(self, event):
        if self.chat_image:  # Check if chat image is loaded
            self.moving_chat = True
            self.start_x = event.x - self.chat_x
            self.start_y = event.y - self.chat_y

    def move_chat(self, event):
        if self.moving_chat:
            self.chat_x = event.x - self.start_x
            self.chat_y = event.y - self.start_y
            if self.is_magnetic_enabled():
                self.apply_magnetic()
            self.draw_images()

    def stop_move_chat(self, event):
        self.moving_chat = False

    def start_selection(self, event):
        if self.chat_image: # Check if chat image is loaded
            self.rect_start_x = event.x
            self.rect_start_y = event.y
            self.rect_id = self.canvas.create_rectangle(self.rect_start_x, self.rect_start_y, event.x, event.y, outline='red')

    def draw_selection(self, event):
        if self.chat_image: # Check if chat image is loaded
            self.canvas.coords(self.rect_id, self.rect_start_x, self.rect_start_y, event.x, event.y)

    def end_selection(self, event):
        if self.chat_image: # Check if chat image is loaded
            x1 = self.rect_start_x
            y1 = self.rect_start_y
            x2 = event.x
            y2 = event.y

            self.selection_coords = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            old_chat_x = self.chat_x
            old_chat_y = self.chat_y

            self.canvas.delete(self.rect_id)
            self.crop_chat()
            self.chat_cropped = True # Setting cropped to True
            self.chat_x = old_chat_x
            self.chat_y = old_chat_y
            self.update_magnetic_state()
            self.save_state()

    def crop_chat(self):
        if self.chat_image and self.selection_coords:
            x1, y1, x2, y2 = self.selection_coords
            img_x1 = x1 - self.chat_x
            img_y1 = y1 - self.chat_y
            img_x2 = x2 - self.chat_x
            img_y2 = y2 - self.chat_y

            # Проверяем, чтобы координаты обрезки были в пределах изображения
            width, height = self.chat_image.size
            img_x1 = max(0, img_x1)
            img_y1 = max(0, img_y1)
            img_x2 = min(width, img_x2)
            img_y2 = min(height, img_y2)

            # Проверяем, что ширина и высота обрезки больше нуля
            if img_x2 - img_x1 > 0 and img_y2 - img_y1 > 0:
                try:
                    cropped_chat = self.chat_image.crop((img_x1, img_y1, img_x2, img_y2))
                    self.chat_image = cropped_chat
                    self.draw_chat()
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка при обрезке: {e}")
            else:
                messagebox.showinfo("Внимание", "Выделенная область слишком мала для обрезки.")

    def add_outline(self):
        if self.chat_image:
            img = self.chat_image.convert("RGBA")

            # Create a mask of the text
            alpha = img.convert('L')

            # Expand the mask (dilate)
            blurred = alpha.filter(ImageFilter.MaxFilter(3))  # Adjust the radius as needed

            # Create a new image for the outline
            new = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(new)

            # Draw the outline
            draw.bitmap((0, 0), blurred, fill="black")  # Outline color

            # Combine the original image with the outline
            self.chat_image = Image.alpha_composite(new, img)  # Drawing new image before
            self.draw_chat()
            self.chat_outlined = True # Setting outlined to True
            self.update_magnetic_state()
            self.save_state()

    def save_image(self):
        #Сохраняем текущее изображение на холсте как файл
        filename = filedialog.asksaveasfilename(defaultextension=".jpg",
                                               filetypes=(("JPEG файлы", "*.jpg"), ("Все файлы", "*.*")))
        if filename:
            try:
                # Создаем новое изображение с нужным размером и белым фоном
                final_image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")

                # Если есть фоновое изображение, вставляем его
                if self.bg_image:
                  final_image.paste(self.bg_image, (self.bg_x, self.bg_y))

                # Если есть чат, вставляем его
                if self.chat_image:
                    final_image.paste(self.chat_image, (self.chat_x, self.chat_y), self.chat_image) # Третий аргумент - маска прозрачности

                # Сохраняем итоговое изображение
                final_image.save(filename)
                messagebox.showinfo("Сохранено", "Изображение успешно сохранено!")
                self.clear_canvas() # Очищаем канву после сохранения
                self.magnetic_override = False
                self.update_magnetic_button_state()
                self.save_state()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении: {e}")

    def save_to_memory(self):
        if len(self.memory) < self.memory_limit:
            # Создаем новое изображение с нужным размером и белым фоном (как в save_image)
            temp_image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")

            # Если есть фоновое изображение, вставляем его
            if self.bg_image:
                temp_image.paste(self.bg_image, (self.bg_x, self.bg_y))

            # Если есть чат, вставляем его
            if self.chat_image:
                temp_image.paste(self.chat_image, (self.chat_x, self.chat_y), self.chat_image) # Третий аргумент - маска прозрачности
            self.memory.append(temp_image)

            self.update_memory_indicator()
            messagebox.showinfo("Память", f"Изображение сохранено в памяти ({len(self.memory)}/{self.memory_limit})")
            self.clear_canvas() # Очищаем канву после сохранения
            self.magnetic_override = False
            self.update_magnetic_button_state()
            self.save_state()
            if len(self.memory) == self.memory_limit:
                self.process_memory() # Автоматически обрабатываем память, если достигнут лимит
        else:
            messagebox.showinfo("Память", "Память заполнена. Обработайте изображения.")

    def process_memory(self):
      if len(self.memory) > 0:
        # Запрашиваем у пользователя количество изображений для объединения
        num_images = simpledialog.askinteger("Количество изображений", "Сколько изображений объединить?",
                                            initialvalue=len(self.memory), minvalue=1, maxvalue=len(self.memory))
        if num_images is None:  # Пользователь отменил ввод
            return

        filename = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                 filetypes=(("JPEG файлы", "*.jpg"), ("Все файлы", "*.*")))
        if filename:
          try:
            # Создаем новое изображение, достаточно высокое, чтобы вместить выбранное количество изображений из памяти
            combined_image = Image.new("RGB", (self.canvas_width, self.canvas_height * num_images), "white")

            # Вставляем изображения из памяти последовательно (вертикально)
            for i in range(num_images):
              combined_image.paste(self.memory[i], (0, i * self.canvas_height))

            # Сохраняем итоговое изображение
            combined_image.save(filename)
            messagebox.showinfo("Сохранено", "Изображения из памяти успешно склеены и сохранены!")
            self.clear_memory() # Очищаем память после обработки
            self.clear_canvas() # Очищаем канву после сохранения
            self.magnetic_override = False
            self.update_magnetic_button_state()
            self.save_state()
          except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при склеивании и сохранении: {e}")
      else:
        messagebox.showinfo("Память", "Недостаточно изображений в памяти для склеивания.")

    def clear_canvas(self):
        #Очищаем холст и сбрасываем изображения
        self.canvas.delete("all")
        self.bg_image = None
        self.bg_image_tk = None
        if self.bg_rect_id:
            self.canvas.delete(self.bg_rect_id)
            self.bg_rect_id = None
        self.chat_image = None
        self.chat_image_tk = None
        if self.chat_rect_id:
            self.canvas.delete(self.chat_rect_id)
            self.chat_rect_id = None
        self.selection_coords = None # Сбрасываем выделенную область
        self.chat_cropped = False # Resetting cropped flag
        self.chat_outlined = False # Resetting outlined flag
        self.magnetic_override = False # Resetting magnetic override
        self.update_magnetic_button_state()
        self.draw_images()
        self.save_state()

    def clear_memory(self):
        #Очищаем память
        self.memory = []
        self.update_memory_indicator()
        self.save_state()

    def change_canvas_size(self):
      # Функция для изменения размера холста
      dlg = CanvasSizeDialog(self.master, self.canvas_width, self.canvas_height)
      self.master.wait_window(dlg.top)

      if dlg.result:
        width = 0
        height = 0
        try:
          width = int(dlg.width_entry.get())
          height = int(dlg.height_entry.get())
        except:
          pass

        if width > 0 and height > 0:
          self.canvas_width = width
          self.canvas_height = height
          self.canvas.config(width=self.canvas_width, height=self.canvas_height)
          self.draw_images()  # Перерисовываем изображения на холсте
        else:
          messagebox.showerror("Ошибка", "Ширина и высота должны быть положительными числами.")
        self.save_state()

    def rescale_background(self, value):
        if self.bg_image:
            scale_factor = float(value)
            width, height = self.bg_image.size
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            self.bg_image_resized = self.bg_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.bg_image_tk = ImageTk.PhotoImage(self.bg_image_resized)
            self.draw_images() # Перерисовываем
            self.save_state()

    def apply_magnetic(self):
      if self.chat_image:
          # Find text boundaries
          bbox = self.chat_image.getbbox()
          if bbox:
              left, top, right, bottom = bbox

              # Apply magnetic to text boundaries
              if abs(self.chat_x + left - self.guide_line_offset) < 10:
                  self.chat_x = self.guide_line_offset - left
              if abs(self.chat_y + top - self.guide_line_offset) < 10:
                  self.chat_y = self.guide_line_offset - top
              if abs(self.chat_y + bottom - (self.canvas_height - self.guide_line_offset)) < 10:
                  self.chat_y = (self.canvas_height - self.guide_line_offset) - bottom

    def toggle_guide_lines(self):
        self.guide_lines_visible = not self.guide_lines_visible
        self.draw_images()
        self.save_state()

    def toggle_magnetic(self):
        self.magnetic_override = not self.magnetic_override
        self.update_magnetic_button_state()
        self.save_state()

    def draw_guide_lines(self):
        if self.guide_lines_visible:
            self.canvas.create_line(self.guide_line_offset, 0, self.guide_line_offset, self.canvas_height, fill="red", dash=(4, 4))
            self.canvas.create_line(0, self.guide_line_offset, self.canvas_width, self.guide_line_offset, fill="red", dash=(4, 4))
            self.canvas.create_line(0, self.canvas_height - self.guide_line_offset, self.canvas_width, self.canvas_height - self.guide_line_offset, fill="red", dash=(4, 4))

    def update_memory_indicator(self):
        self.memory_indicator.config(text=f"В памяти: {len(self.memory)}/{self.memory_limit}")

    def is_magnetic_enabled(self):
        return (self.chat_cropped and self.chat_outlined and not self.magnetic_override) or (self.magnetic_override and self.chat_cropped and self.chat_outlined)

    def update_magnetic_state(self):
        if self.chat_cropped and self.chat_outlined:
            self.toggle_magnetic_button.config(state=tk.NORMAL)
        else:
            self.toggle_magnetic_button.config(state=tk.DISABLED)

        if self.is_magnetic_enabled():
            self.toggle_magnetic_button.config(text="Выключить Примагничивание", relief=tk.SUNKEN)
        else:
            self.toggle_magnetic_button.config(text="Включить Примагничивание", relief=tk.RAISED)

    def update_magnetic_button_state(self):
        if self.is_magnetic_enabled():
            self.toggle_magnetic_button.config(text="Выключить Примагничивание", relief=tk.SUNKEN, bg="green")
        else:
            self.toggle_magnetic_button.config(text="Включить Примагничивание", relief=tk.RAISED, bg="SystemButtonFace")

    def start_delete_selection(self, event):
        if self.chat_image: # Check if chat image is loaded
            self.delete_rect_start_x = event.x
            self.delete_rect_start_y = event.y
            self.delete_rect_id = self.canvas.create_rectangle(self.delete_rect_start_x, self.delete_rect_start_y, event.x, event.y, outline='red')
            self.canvas.bind("<B1-Motion>", self.draw_delete_selection)
            self.canvas.bind("<ButtonRelease-1>", self.end_delete_selection)

    def draw_delete_selection(self, event):
        if self.chat_image: # Check if chat image is loaded
            self.canvas.coords(self.delete_rect_id, self.delete_rect_start_x, self.delete_rect_start_y, event.x, event.y)

    def end_delete_selection(self, event):
        if self.chat_image: # Check if chat image is loaded
            x1 = self.delete_rect_start_x
            y1 = self.delete_rect_start_y
            x2 = event.x
            y2 = event.y

            self.delete_coords = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

            self.canvas.delete(self.delete_rect_id)
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            self.delete_selection()
            self.save_state()

    def delete_selection(self):
        if self.chat_image and self.delete_coords:
            x1, y1, x2, y2 = self.delete_coords
            img_x1 = x1 - self.chat_x
            img_y1 = y1 - self.chat_y
            img_x2 = x2 - self.chat_x
            img_y2 = y2 - self.chat_y

            draw = ImageDraw.Draw(self.chat_image)
            draw.rectangle((img_x1, img_y1, img_x2, img_y2), fill=(0, 0, 0, 0))  # Make it transparent

            self.draw_chat()

    def save_state(self):
        # Save current state to history
        state = {
            "bg_image": self.bg_image.copy() if self.bg_image else None,
            "chat_image": self.chat_image.copy() if self.chat_image else None,
            "bg_x": self.bg_x,
            "bg_y": self.bg_y,
            "chat_x": self.chat_x,
            "chat_y": self.chat_y,
            "chat_cropped": self.chat_cropped,
            "chat_outlined": self.chat_outlined,
            "magnetic_override": self.magnetic_override,
            "memory": [img.copy() for img in self.memory],
        }
        # Trim history if we've undone
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append(state)
        self.history_index += 1
        print("Saved state to history, index:", self.history_index) # For debugging

        # Limit history size
        if len(self.history) > 10:
          self.history = self.history[-10:]
          self.history_index = len(self.history) - 1

    def undo(self, event=None):
        # Undo to previous state
        if self.history_index > 0:
            self.history_index -= 1
            state = self.history[self.history_index]
            self.load_state(state)
            print("Undoing, current index:", self.history_index)  # For debugging

    def redo(self, event=None):
        # Redo to next state
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            state = self.history[self.history_index]
            self.load_state(state)
            print("Redoing, current index:", self.history_index) # For debugging

    def load_state(self, state):
        # Load state from history
        self.bg_image = state["bg_image"]
        self.chat_image = state["chat_image"]
        self.bg_x = state["bg_x"]
        self.bg_y = state["bg_y"]
        self.chat_x = state["chat_x"]
        self.chat_y = state["chat_y"]
        self.chat_cropped = state["chat_cropped"]
        self.chat_outlined = state["chat_outlined"]
        self.magnetic_override = state["magnetic_override"]
        self.memory = [img.copy() for img in state["memory"]]

        # Update UI
        if self.bg_image:
            self.bg_image_tk = ImageTk.PhotoImage(self.bg_image)
        else:
            self.bg_image_tk = None

        if self.chat_image:
            self.chat_image_tk = ImageTk.PhotoImage(self.chat_image)
        else:
            self.chat_image_tk = None

        self.update_memory_indicator()
        self.update_magnetic_button_state()
        self.draw_images()

class CanvasSizeDialog:
    def __init__(self, parent, width, height):
        self.top = tk.Toplevel(parent)
        self.top.transient(parent)
        self.top.grab_set()

        self.result = None

        tk.Label(self.top, text="Ширина:").grid(row=0, column=0, padx=5, pady=5)
        tk.Label(self.top, text="Высота:").grid(row=1, column=0, padx=5, pady=5)

        self.width_entry = tk.Entry(self.top)
        self.width_entry.insert(0, str(width))
        self.width_entry.grid(row=0, column=1, padx=5, pady=5)

        self.height_entry = tk.Entry(self.top)
        self.height_entry.insert(0, str(height))
        self.height_entry.grid(row=1, column=1, padx=5, pady=5)

        ok_button = tk.Button(self.top, text="OK", command=self.ok)
        ok_button.grid(row=2, column=0, padx=5, pady=5)

        cancel_button = tk.Button(self.top, text="Отмена", command=self.cancel)
        cancel_button.grid(row=2, column=1, padx=5, pady=5)

        self.top.bind("<Return>", self.ok)
        self.top.bind("<Escape>", self.cancel)

    def ok(self, event=None):
        try:
            width = int(self.width_entry.get())
            height = int(self.height_entry.get())
            self.result = (width, height)
            self.top.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Пожалуйста, введите целые числа для ширины и высоты.")

    def cancel(self, event=None):
        self.result = None
        self.top.destroy()

root = tk.Tk()
processor = ImageProcessor(root)
root.mainloop()