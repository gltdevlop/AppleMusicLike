from tkinter import messagebox
import lyricsgenius
import pygame
from tkinter import *
from PIL import Image, ImageTk, ImageFilter
import threading
import yt_dlp
import ssl
import requests
from io import BytesIO
import os
from PIL.ImagePalette import wedge
from lrclib import LrcLibAPI
from googleapiclient.discovery import build


def load_api_keys(file_path="api_keys.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            keys = f.readlines()
            youtube_key = keys[0].strip()
            genius_key = keys[1].strip()
            return youtube_key, genius_key
    except FileNotFoundError:
        messagebox.showerror("Erreur", f"Le fichier {file_path} est introuvable.")
        exit()
    except IndexError:
        messagebox.showerror("Erreur", f"Le fichier {file_path} est incomplet. Assurez-vous qu'il contient deux clés.")
        exit()


youtube_api_key, genius_api_key = load_api_keys()
genius = lyricsgenius.Genius(genius_api_key)

def chercher_lien_youtube(titre_chanson, artiste, api_key):
    # Initialisation du client API YouTube
    youtube = build('youtube', 'v3', developerKey=api_key)

    # Requête de recherche sur YouTube
    requete = youtube.search().list(
        part='snippet',
        q=f'{titre_chanson} {artiste} topic',
        type='video',
        maxResults=1,
        videoCategoryId='10',  # Catégorie Musique
    )

    resultats = requete.execute()

    if resultats['items']:
        video_id = resultats['items'][0]['id']['videoId']
        lien_youtube = f'https://www.youtube.com/watch?v={video_id}'
        return lien_youtube
    else:
        return "Aucune vidéo trouvée."

# Fonction pour télécharger l'audio depuis YouTube
def download_audio_and_lrc(link, song_title, artist_name):
    formatted_title = song_title.replace(" ", "-")
    formatted_artist = artist_name.replace(" ", "-")
    filename = f"songs/{formatted_title}_{formatted_artist}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': filename,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
    print("Téléchargement terminé")

    formatted_title = song_title.replace(" ", "-")
    formatted_artist = artist_name.replace(" ", "-")
    lrc_filename = f"lrc/{formatted_title}_{formatted_artist}.lrc"
    api = LrcLibAPI(user_agent="my-app/0.0.1")
    try:
        lyrics = api.get_lyrics(
            track_name=formatted_title,
            artist_name=formatted_artist,
        )
        found_lyrics = lyrics.synced_lyrics or lyrics.plain_lyrics

        if not found_lyrics:
            print("Aucune parole trouvée pour cette chanson.")

    except Exception as e:
        if hasattr(e, 'status_code') and e.status_code == 404:
            messagebox.showerror("Erreur", "Impossible de trouver des paroles. Merci de vérifier"
                                           " le nom de l'artiste et de la chanson.")
            os.remove(f"{filename}.mp3")
        else:
            print(f"Une erreur s'est produite : {e}")

    if found_lyrics:
        with open(lrc_filename, "w", encoding="utf-8") as lrc_file:
            lrc_file.write(f"[00:00.00] ...\n")
            lrc_file.write(f"[00:00.01] {song_title} - {artist_name}\n")
            lrc_file.write("\n".join(found_lyrics.split("\n")))
            lrc_file.write("AppleMusiclike - gltdevlop / l'herbag")
        print(f"Fichier LRC enregistré : {lrc_filename}")
        return lrc_filename

    else:
        print("Paroles non trouvées et aucun fichier n'a été créé.")

    return f"{filename}.mp3"


# Fonction pour récupérer et formater les paroles synchronisées au format LRC depuis l'API lrclib


def get_cover(song_title, artist_name, album_name=None):
    # Si un album est fourni, inclure dans la recherche
    query = f"{song_title} {artist_name}"
    if album_name:
        query += f" {album_name}"

    song = genius.search_song(query)
    if song:
        cover_url = song.song_art_image_url
        return cover_url, song.title, song.artist
    return None, "", ""


# Fonction pour télécharger l'image de couverture
def download_cover_image(cover_url):
    response = requests.get(cover_url)
    img_data = BytesIO(response.content)
    cover_image = Image.open(img_data)
    return cover_image


# Classe principale pour l'application
class MusicPlayer:
    def __init__(self, root, audio_file, lrc_file, cover_image, song_title, artist_name):
        if cover_image is None:
            messagebox.showerror("Erreur", "Image de couverture introuvable. Veuillez vérifier les informations de la chanson.")
            root.destroy()  # Ferme la fenêtre si l'image est absente
            return

        self.root = root
        self.root.title("Music Player")
        self.audio_file = audio_file
        self.is_playing = True
        self.current_line_index = 0

        root.resizable(False, False)

        # Passer à plein écran
        self.root.attributes('-fullscreen', True)

        # Créer un canvas comme fond d'écran pour simuler la transparence
        self.canvas = Canvas(root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=True)

        # Charger les paroles synchronisées depuis le fichier LRC
        self.lyrics = self.load_lyrics_from_lrc(lrc_file)
        self.cover_image = cover_image
        self.update_background()

        # Configuration et mise en place des éléments d'interface
        self.root.bind("<Configure>", self.resize_elements)
        cover_resized = self.cover_image.resize((350, 350))
        self.cover_image_tk = ImageTk.PhotoImage(cover_resized)
        self.cover_label = Label(self.canvas, image=self.cover_image_tk, bg="black")
        self.cover_label.place(relx=0.285, rely=0.475, anchor=CENTER)

        self.song_info_label = Label(
            self.canvas, text=f"{song_title} - {artist_name}", font=("SF Pro", 20, "bold"),
            fg="white", bg="black", relief=FLAT
        )
        self.song_info_label.place(relx=0.285, rely=0.676, anchor=CENTER)

        self.lyrics_label = Label(
            self.canvas, text="", font=("SF Pro", 25, "bold"), fg="white",
            justify=CENTER, wraplength=600, bg="black"
        )
        self.lyrics_label.place(relx=0.68, rely=0.5, anchor=CENTER)

        self.previous_lyric_label = Label(
            self.canvas, text="", font=("SF Pro", 22), fg="lightgray", bg="black",
            justify=LEFT
        )
        self.previous_lyric_label.place(relx=0.68, rely=0.42, anchor=CENTER)

        self.next_lyric_label = Label(
            self.canvas, text="", font=("SF Pro", 22), fg="lightgray", bg="black",
            justify=LEFT
        )
        self.next_lyric_label.place(relx=0.68, rely=0.58, anchor=CENTER)

        play_icon_img = Image.open("icons/play_icon.png").resize((30, 30))
        pause_icon_img = Image.open("icons/pause_icon.png").resize((30, 30))
        self.play_icon = ImageTk.PhotoImage(play_icon_img)
        self.pause_icon = ImageTk.PhotoImage(pause_icon_img)

        # Créer le bouton avec l'icône de pause par défaut
        self.play_pause_button = Button(
            self.canvas, image=self.pause_icon, command=self.toggle_play_pause,
            bg="black", activebackground="black", borderwidth=0
        )
        self.play_pause_button.place(relx=0.285, rely=0.74, anchor=CENTER)

        pygame.mixer.init()
        pygame.mixer.music.load(self.audio_file)

        self.start_music()

    def start_music(self):
        pygame.mixer.music.play()
        self.show_lyrics()  # Appel ici pour démarrer l'affichage des paroles

    def toggle_play_pause(self):
        if self.is_playing:
            pygame.mixer.music.pause()
            self.play_pause_button.config(text="Play")
            self.is_playing = False
        else:
            pygame.mixer.music.unpause()
            self.play_pause_button.config(text="Pause")
            self.is_playing = True

    def show_lyrics(self):
        def display_next_line():
            if self.current_line_index < len(self.lyrics):
                current_lyric, timestamp = self.lyrics[self.current_line_index]

                current_time = pygame.mixer.music.get_pos() / 1000

                if current_time >= (timestamp - 0.5):
                    self.lyrics_label.config(text=current_lyric)
                    if self.current_line_index > 0:
                        self.previous_lyric_label.config(text=self.lyrics[self.current_line_index - 1][0])
                    else:
                        self.previous_lyric_label.config(text="")

                    if self.current_line_index < len(self.lyrics) - 1:
                        self.next_lyric_label.config(text=self.lyrics[self.current_line_index + 1][0])
                    else:
                        self.next_lyric_label.config(text="")
                    print(
                        f"Displaying lyric: {current_lyric} at {timestamp}, current time: {current_time}")
                    self.current_line_index += 1

            self.root.after(100, display_next_line)

        display_next_line()

    def update_background(self):
        if self.cover_image.mode != "RGB":  # S'assurer que l'image est en mode RGB
            self.cover_image = self.cover_image.convert("RGB")

        blurred_bg = self.cover_image.resize((self.root.winfo_screenwidth(), self.root.winfo_screenheight()))
        blurred_bg = blurred_bg.filter(ImageFilter.GaussianBlur(25))
        self.bg_image = ImageTk.PhotoImage(blurred_bg)
        self.canvas.create_image(0, 0, image=self.bg_image, anchor=NW)

    def load_lyrics_from_lrc(self, lrc_file):
        lyrics = []
        try:
            with open(lrc_file, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("[") and "] " in line:
                        try:
                            time_tag, text = line.split("] ", 1)
                            minutes, seconds = map(float, time_tag[1:].split(":"))
                            timestamp = minutes * 60 + seconds
                            lyrics.append((text, timestamp))
                            print(f"Loaded lyric: {text} at {timestamp}")  # Debug statement
                        except ValueError:
                            print(f"Line skipped due to parsing error: {line}")
                    else:
                        print(f"Line skipped (not valid): {line}")
        except FileNotFoundError:
            messagebox.showerror("Erreur", "Le Fichier LRC n'eiste pas. Merci de réessayer.")
            exit()
        return lyrics

    def resize_elements(self, event=None):
        self.lyrics_label.config(wraplength=self.root.winfo_width() * 0.6)
        self.cover_label.place(relx=0.285, rely=0.475, anchor=CENTER)
        self.song_info_label.place(relx=0.285, rely=0.676, anchor=CENTER)
        self.lyrics_label.place(relx=0.68, rely=0.5, anchor=CENTER)
        self.previous_lyric_label.place(relx=0.68, rely=0.45, anchor=CENTER)
        self.next_lyric_label.place(relx=0.68, rely=0.55, anchor=CENTER)


# Classe pour la fenêtre de sélection
class SelectionWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Sélection de musique")

        self.frame = Frame(self.root, bg="black")
        self.frame.pack(fill=BOTH, expand=True)

        # Liste des chansons téléchargées
        self.song_list = Listbox(self.frame, bg="gray", fg="white", font=("SF Pro", 15), selectbackground="black")
        self.song_list.pack(fill=BOTH, expand=True, side=LEFT)

        # Dictionnaire pour correspondre le nom affiché à son fichier d'origine
        self.song_files = {}

        self.load_downloaded_songs()

        # Frame de téléchargement
        self.download_frame = Frame(self.frame, bg="black")
        self.download_frame.pack(fill=X, side=BOTTOM)

        Label(self.download_frame, text="Titre:", bg="black", fg="white").grid(row=1, column=0, padx=5, pady=5)
        self.song_title_entry = Entry(self.download_frame)
        self.song_title_entry.grid(row=1, column=1, padx=5, pady=5)

        Label(self.download_frame, text="Artiste:", bg="black", fg="white").grid(row=2, column=0, padx=5, pady=5)
        self.artist_name_entry = Entry(self.download_frame)
        self.artist_name_entry.grid(row=2, column=1, padx=5, pady=5)

        # Ajout du champ pour l'album
        Label(self.download_frame, text="Album (optionnel):", bg="black", fg="white").grid(row=3, column=0, padx=5, pady=5)
        self.album_name_entry = Entry(self.download_frame)
        self.album_name_entry.grid(row=3, column=1, padx=5, pady=5)

        Button(self.download_frame, text="Télécharger", command=self.download_song).grid(row=4, column=0, columnspan=2,
                                                                                         pady=10)

        self.song_list.bind("<Double-Button-1>", self.launch_music_player)

    def load_downloaded_songs(self):
        self.song_list.delete(0, END)  # Supprimer tous les éléments existants de la liste
        self.song_files = {}  # Réinitialiser le dictionnaire de correspondance

        for filename in os.listdir("songs"):
            if filename.endswith(".mp3"):
                # Extraire le titre de la chanson et le nom de l'artiste depuis le nom du fichier
                song_title_artist = filename.rsplit("_", 1)  # Diviser pour obtenir le titre et l'artiste
                if len(song_title_artist) < 2:
                    print(f"Fichier ignoré (format incorrect): {filename}")  # Débogage
                    continue  # Ignorer les fichiers qui ne correspondent pas au format attendu

                song_title = song_title_artist[0].replace("-", " ")  # Remplacer les traits d'union par des espaces
                artist_name = song_title_artist[1].replace(".mp3", "").replace("_", " ")  # Remplacer les underscores

                display_name = f"{song_title} - {artist_name}"

                # Ajouter le nom formaté à la liste et stocker le fichier original
                self.song_list.insert(END, display_name)  # Ajouter à la liste
                self.song_files[display_name] = filename  # Associer le nom affiché au nom de fichier réel
                print(f"Chanson ajoutée: {display_name}")  # Débogage
        if not self.song_files:
            print("Aucune chanson trouvée dans le répertoire 'songs'.")  # Débogage

    def download_song(self):
        song_title = self.song_title_entry.get()
        artist_name = self.artist_name_entry.get()
        album_name = self.album_name_entry.get()  # Récupérer le nom de l'album

        if song_title and artist_name:
            link = chercher_lien_youtube(song_title, artist_name, youtube_api_key)
            audio_file = download_audio_and_lrc(link, song_title, artist_name)

            if not os.path.exists(audio_file):  # Vérifier si le fichier audio existe
                messagebox.showerror("Erreur", "Le fichier audio n'a pas été téléchargé avec succès.")
                return

            lrc_file = f"lrc/{song_title.replace(' ', '-')}_{artist_name.replace(' ', '-')}.lrc"
            if not os.path.exists(lrc_file):  # Vérifier si le fichier LRC existe
                messagebox.showwarning("Avertissement", "Les paroles synchronisées n'ont pas été trouvées.")

            # Ajouter à la liste des chansons après validation
            display_name = f"{song_title} - {artist_name}"
            self.song_list.insert(END, display_name)
            self.song_files[display_name] = os.path.basename(audio_file)

            # Effacer les champs de saisie après téléchargement
            self.song_title_entry.delete(0, END)
            self.artist_name_entry.delete(0, END)
            self.album_name_entry.delete(0, END)  # Réinitialiser le champ de l'album
            print("Téléchargement effectué")

            self.load_downloaded_songs()

    def launch_music_player(self, event):
        selected_display_name = self.song_list.get(self.song_list.curselection())
        filename = self.song_files[selected_display_name]  # Récupérer le nom de fichier réel

        # Extraire le titre de la chanson et l'artiste
        song_title, artist_name = filename.rsplit("_", 1)[0], filename.rsplit("_", 1)[1].replace(".mp3", "")

        audio_file = f"songs/{filename}"
        lrc_file = f"lrc/{song_title}_{artist_name}.lrc"

        # Récupérer le nom de l'album s'il existe
        album_name = self.album_name_entry.get() if self.album_name_entry else None
        cover_url, song_title, artist_name = get_cover(song_title, artist_name, album_name)

        if cover_url:
            cover_image = download_cover_image(cover_url)
        else:
            messagebox.showerror("Erreur", f"Aucune image de couverture trouvée pour {song_title} - {artist_name}.")
            return  # Arrêter ici si aucune couverture n'est trouvée

        player_window = Toplevel(self.root)
        player_window.configure(bg="black")
        try:
            player = MusicPlayer(player_window, audio_file, lrc_file, cover_image, song_title, artist_name)
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue lors du lancement du lecteur : {e}")
            player_window.destroy()  #   Fermer la fenêtre en cas d'erreur


# Fonction principale
def main():
    root = Tk()
    app = SelectionWindow(root)
    root.geometry("600x250")
    root.mainloop()


if __name__ == "__main__":
    main()
