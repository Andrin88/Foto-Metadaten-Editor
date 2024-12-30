import os
from tkinter import Tk, Label, Entry, Button, filedialog, StringVar
from tkinter import messagebox
from PIL import Image, ImageTk
import piexif
from datetime import datetime

class PhotoMetadataEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Foto-Metadaten-Editor")

        # Aktuelles Bild und Verzeichnis
        self.image_index = 0
        self.images = []
        self.current_image = None
        self.persons_list = []  # Zwischenspeicher für Personen eines Bildes
        self.output_dir = "output"  # Standard-Ausgabeverzeichnis

        # GUI-Elemente
        self.label_image = Label(root)
        self.label_image.pack()

        self.name_var = StringVar()
        self.entry_persons = Entry(root, textvariable=self.name_var, width=50)
        self.entry_persons.pack()
        self.entry_persons.bind("<Return>", self.add_person)  # Enter fügt einen Namen hinzu

        self.entry_location = Entry(root, width=50)
        self.entry_location.pack()
        self.entry_location.insert(0, "Ort der Aufnahme")
        self.entry_location.bind("<Return>", lambda event: self.entry_date.focus_set())  # Enter springt zu Datum

        self.entry_date = Entry(root, width=50)
        self.entry_date.pack()
        self.entry_date.insert(0, "TT.MM.JJJJ (Datum der Aufnahme)")
        self.entry_date.bind("<Return>", lambda event: self.save_metadata())  # Enter speichert

        self.metadata_label = Label(root, text="", justify="left")
        self.metadata_label.pack()

        Button(root, text="Bildverzeichnis auswählen", command=self.select_directory).pack()
        Button(root, text="Ausgabeverzeichnis auswählen", command=self.select_output_directory).pack()
        Button(root, text="Speichern", command=self.save_metadata).pack()
        Button(root, text="Vorheriges Bild", command=self.prev_image).pack(side="left")
        Button(root, text="Nächstes Bild", command=self.next_image).pack(side="right")

        # Tastenbindungen für Navigation
        root.bind("<Left>", lambda event: self.prev_image())
        root.bind("<Right>", lambda event: self.next_image())

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.images = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            self.image_index = 0
            self.show_image()

    def select_output_directory(self):
        """Öffnet ein Dialogfeld, um das Ausgabeverzeichnis auszuwählen."""
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir = directory
            messagebox.showinfo("Ausgabeverzeichnis", f"Das Ausgabeverzeichnis wurde auf '{self.output_dir}' gesetzt.")

    def show_image(self):
        if not self.images:
            return
        image_path = self.images[self.image_index]
        self.current_image = image_path
        image = Image.open(image_path)
        image.thumbnail((800, 600))
        photo = ImageTk.PhotoImage(image)
        self.label_image.config(image=photo)
        self.label_image.image = photo
        self.display_metadata()

    def display_metadata(self):
        """Liest und zeigt die aktuellen Metadaten des Bildes an."""
        if not self.current_image:
            return

        try:
            exif_dict = piexif.load(self.current_image)
            user_comment = exif_dict['Exif'].get(piexif.ExifIFD.UserComment, b"").decode('utf-8', errors='ignore')

            if user_comment:
                metadata = dict(pair.split(": ") for pair in user_comment.split(", ") if ": " in pair)
                persons = metadata.get("Persons", "")
                location = metadata.get("Location", "")
                date = metadata.get("Date", "")

                self.persons_list = persons.split(", ") if persons else []
                self.entry_persons.delete(0, "end")
                self.entry_location.delete(0, "end")
                self.entry_date.delete(0, "end")

                self.entry_location.insert(0, location)
                self.entry_date.insert(0, date)

                self.metadata_label.config(text=f"Metadaten:\nNamen: {', '.join(self.persons_list)}\nOrt: {location}\nDatum: {date}")
            else:
                self.metadata_label.config(text="Metadaten: Keine Informationen vorhanden.")
                self.persons_list = []

        except Exception as e:
            print(f"Fehler beim Laden der Metadaten: {e}")
            self.metadata_label.config(text="Fehler beim Laden der Metadaten.")

    def add_person(self, event=None):
        """Fügt einen Namen hinzu und leert das Eingabefeld."""
        person = self.name_var.get().strip()
        if person:
            self.persons_list.append(person)
            self.name_var.set("")  # Eingabefeld leeren
            self.metadata_label.config(text=f"Namen: {', '.join(self.persons_list)}")

    def save_metadata(self):
        """Speichert Metadaten in die EXIF-Daten des Bildes."""
        persons = ", ".join(self.persons_list)
        location = self.entry_location.get()
        date = self.entry_date.get()

        if not self.current_image:
            return

        try:
            # Validierung und Formatierung des Datums
            try:
                date = datetime.strptime(date, "%d.%m.%Y").strftime("%d.%m.%Y")
            except ValueError:
                messagebox.showerror("Fehler", "Falsches Datumsformat (TT.MM.JJJJ erforderlich).")
                return

            # Metadaten speichern
            exif_dict = piexif.load(self.current_image)

            # Falls keine EXIF-Daten existieren, erstellen wir sie neu
            if "Exif" not in exif_dict:
                exif_dict["Exif"] = {}

            user_comment = f"Persons: {persons}, Location: {location}, Date: {date}"
            exif_dict['Exif'][piexif.ExifIFD.UserComment] = user_comment.encode('utf-8')

            print("Debug: EXIF-Daten vor dem Speichern:", exif_dict)

            self.save_image_with_metadata(exif_dict)

            # Rückmeldung anzeigen
            self.metadata_label.config(text="Metadaten erfolgreich gespeichert.")
            print(f"Gespeicherte Metadaten: {user_comment}")

        except Exception as e:
            print(f"Fehler beim Speichern der Metadaten: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Speichern der Metadaten: {e}")

    def save_image_with_metadata(self, exif_dict):
        """Speichert das Bild mit den aktualisierten Metadaten im gewählten Verzeichnis."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        output_path = os.path.join(self.output_dir, os.path.basename(self.current_image))
        exif_bytes = piexif.dump(exif_dict)

        image = Image.open(self.current_image)
        image.save(output_path, "jpeg", exif=exif_bytes)
        print(f"Bild gespeichert in: {output_path}")

    def next_image(self):
        if self.images:
            self.image_index = (self.image_index + 1) % len(self.images)
            self.show_image()

    def prev_image(self):
        if self.images:
            self.image_index = (self.image_index - 1) % len(self.images)
            self.show_image()


if __name__ == "__main__":
    root = Tk()
    editor = PhotoMetadataEditor(root)
    root.mainloop()
