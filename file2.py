import os
import sys
import pygame
import requests
from io import BytesIO
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QLineEdit)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer


# Fonction pour télécharger l'audio depuis YouTube (à implémenter avec yt_dlp si nécessaire)
def download_audio(youtube_url, song_title, artist_name):
    filename = f"songs/{song_title.replace(' ', '_')}_{artist_name.replace(' ', '_')}.mp3"
    # Simuler la création du fichier
    with open(filename, 'wb') as f:
        f.write(b'Simulated audio file content')
    return filename


# Fonction pour télécharger une image de couverture
def download_cover_image(cover_url):
    try:
        response = requests.get(cover_url)
        img_data = BytesIO(response.content)
        cover_image = Image.open(img_data)
        return cover_image
    except Exception as e:
        print(f"Erreur lors du téléchargement de l'image de couverture : {e}")
        return None


# Fonction pour lire un fichier LRC et retourner les paroles synchronisées
def parse_lrc_file(lrc_filename):
    lyrics = []
    try:
        with open(lrc_filename, 'r') as f:
            for line in f:
                if line.startswith('['):
                    time_part, lyric = line.split(']', 1)
                    minutes, seconds = map(float, time_part[1:].split(':'))
                    timestamp = minutes * 60 + seconds
                    lyrics.append((lyric.strip(), timestamp))
    except FileNotFoundError:
        print(f"Fichier LRC {lrc_filename} non trouvé.")
    return lyrics


# Classe pour la fenêtre de sélection
class SelectionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sélection de musique")
        self.setGeometry(100, 100, 600, 400)

        # Liste des chansons téléchargées
        self.song_list = QListWidget()
        self.song_list.setStyleSheet("background-color: gray; color: white; font-size: 18px;")
        self.song_list.itemDoubleClicked.connect(self.launch_music_player)

        # Interface de téléchargement
        self.url_entry = QLineEdit(self)
        self.url_entry.setPlaceholderText("Lien YouTube")
        self.title_entry = QLineEdit(self)
        self.title_entry.setPlaceholderText("Titre de la chanson")
        self.artist_entry = QLineEdit(self)
        self.artist_entry.setPlaceholderText("Nom de l'artiste")

        # Bouton de téléchargement
        self.download_button = QPushButton("Télécharger")
        self.download_button.clicked.connect(self.download_song)

        # Layout principal
        layout = QVBoxLayout()
        layout.addWidget(self.song_list)
        layout.addWidget(self.url_entry)
        layout.addWidget(self.title_entry)
        layout.addWidget(self.artist_entry)
        layout.addWidget(self.download_button)

        self.setLayout(layout)
        self.load_downloaded_songs()

    def load_downloaded_songs(self):
        self.song_list.clear()
        for filename in os.listdir("songs"):
            if filename.endswith(".mp3"):
                display_name = filename.replace("_", " ").replace(".mp3", "")
                self.song_list.addItem(display_name)

    def download_song(self):
        youtube_url = self.url_entry.text()
        song_title = self.title_entry.text()
        artist_name = self.artist_entry.text()
        if youtube_url and song_title and artist_name:
            audio_file = download_audio(youtube_url, song_title, artist_name)
            display_name = f"{song_title} - {artist_name}"
            self.song_list.addItem(display_name)
            print("Téléchargement terminé")
        else:
            print("Veuillez remplir tous les champs pour télécharger une chanson.")

    def launch_music_player(self, item):
        song_name = item.text()
        if " - " in song_name:
            song_title, artist_name = song_name.split(" - ", 1)
            audio_file = f"songs/{song_title.replace(' ', '_')}_{artist_name.replace(' ', '_')}.mp3"
            lrc_file = audio_file.replace('.mp3', '.lrc')
            cover_url = f"https://fake-cover-url/{song_title}_{artist_name}.jpg"  # Remplacez par une URL valide
            cover_image = download_cover_image(cover_url)

            player = MusicPlayer(audio_file, song_title, artist_name, cover_image, lrc_file)
            player.show()
        else:
            print("Format de nom de chanson invalide")


# Classe pour le lecteur de musique
class MusicPlayer(QWidget):
    def __init__(self, audio_file, song_title, artist_name, cover_image, lrc_file):
        super().__init__()
        self.setWindowTitle("Music Player")
        self.setGeometry(200, 200, 800, 600)
        self.audio_file = audio_file
        self.song_title = song_title
        self.artist_name = artist_name
        self.cover_image = cover_image
        self.lyrics = parse_lrc_file(lrc_file)
        self.current_lyric_index = 0

        # Titre et artiste
        self.title_label = QLabel(f"{song_title} - {artist_name}")
        self.title_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.title_label.setStyleSheet("color: white; background: transparent;")

        # Image de couverture
        cover_label = QLabel(self)
        if cover_image:
            cover_pixmap = QPixmap(self.cover_image).scaled(350, 350, Qt.KeepAspectRatio)
            cover_label.setPixmap(cover_pixmap)

        # Bouton Play/Pause
        self.play_button = QPushButton("Pause")
        self.play_button.clicked.connect(self.toggle_play_pause)

        # Label pour les paroles
        self.lyric_label = QLabel("")
        self.lyric_label.setFont(QFont("Arial", 18))
        self.lyric_label.setStyleSheet("color: white; background: transparent;")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(cover_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.play_button)
        layout.addWidget(self.lyric_label)
        self.setLayout(layout)

        # Initialisation de pygame pour la musique
        pygame.mixer.init()
        pygame.mixer.music.load(self.audio_file)
        pygame.mixer.music.play()

        # Affichage des paroles synchronisées
        self.show_lyrics()

    def toggle_play_pause(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.play_button.setText("Play")
        else:
            pygame.mixer.music.unpause()
            self.play_button.setText("Pause")

    def show_lyrics(self):
        def display_next_line():
            if self.current_lyric_index < len(self.lyrics):
                current_lyric, timestamp = self.lyrics[self.current_lyric_index]
                current_time = pygame.mixer.music.get_pos() / 1000

                if current_time >= timestamp:
                    self.lyric_label.setText(current_lyric)
                    self.current_lyric_index += 1

            QTimer.singleShot(100, display_next_line)

        display_next_line()


# Fonction principale
def main():
    if not os.path.exists("songs"):
        os.makedirs("songs")
    app = QApplication(sys.argv)
    selection_window = SelectionWindow()
    selection_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
