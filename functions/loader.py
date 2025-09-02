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
