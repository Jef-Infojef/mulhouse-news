import os
import json
import threading
import time
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkcalendar import DateEntry
import psycopg2
from dotenv import load_dotenv

# Tentative d'import du décodeur
try:
    from googlenewsdecoder import gnewsdecoder
except ImportError:
    gnewsdecoder = None

# Charger les variables depuis .env.local
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env.local")
load_dotenv(env_path)

# Récupération de l'URL Supabase
NEWS_DB_URL = os.environ.get("NEWS_DATABASE_URL")
CITY = "Mulhouse"
HISTORY_FILE = os.path.join(script_dir, "scraped_days.json")

class NewsScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mulhouse Actu Manager - Scraper & History")
        self.root.geometry("800x650")
        self.root.configure(bg="#f3f4f6")
        
        self.history = self.load_history()
        self.stop_requested = False
        
        self.setup_ui()
        
        # Log de démarrage
        if NEWS_DB_URL:
            host = NEWS_DB_URL.split("@")[-1].split("/")[0] if "@" in NEWS_DB_URL else "???"
            self.log(f"✅ Configuration chargée. DB Host: {host}")
        else:
            self.log("❌ ERREUR: NEWS_DATABASE_URL non trouvée dans .env.local")
        
    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                try:
                    return json.load(f)
                except:
                    return []
        return []

    def save_history(self, day_str):
        if day_str not in self.history:
            self.history.append(day_str)
            try:
                with open(HISTORY_FILE, "w") as f:
                    json.dump(self.history, f)
            except:
                pass

    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Helvetica', 10))
        style.configure("Header.TLabel", font=('Helvetica', 14, 'bold'), background="#f3f4f6")

        # Main Container
        main_frame = tk.Frame(self.root, bg="#f3f4f6", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="🚀 News Scraper & History Manager", font=("Helvetica", 16, "bold"), bg="#f3f4f6", fg="#1e293b").pack(pady=(0, 20))

        # Date Selection Frame
        date_frame = tk.LabelFrame(main_frame, text=" Période de Scraping ", bg="#f3f4f6", padx=15, pady=15)
        date_frame.pack(fill=tk.X, pady=10)

        tk.Label(date_frame, text="Début :", bg="#f3f4f6").grid(row=0, column=0, padx=5)
        self.start_cal = DateEntry(date_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
        self.start_cal.grid(row=0, column=1, padx=10)

        tk.Label(date_frame, text="Fin :", bg="#f3f4f6").grid(row=0, column=2, padx=5)
        self.end_cal = DateEntry(date_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
        self.end_cal.grid(row=0, column=3, padx=10)

        self.skip_scraped_var = tk.BooleanVar(value=True)
        tk.Checkbutton(date_frame, text="Sauter les jours déjà faits", variable=self.skip_scraped_var, bg="#f3f4f6").grid(row=0, column=4, padx=20)

        # Buttons Frame
        btn_frame = tk.Frame(main_frame, bg="#f3f4f6")
        btn_frame.pack(fill=tk.X, pady=10)

        self.start_btn = tk.Button(btn_frame, text="Démarrer le Scraping", command=self.start_scraping, bg="#10b981", fg="white", font=("Helvetica", 10, "bold"), relief=tk.FLAT, padx=20)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(btn_frame, text="Arrêter", command=self.stop_scraping, bg="#ef4444", fg="white", font=("Helvetica", 10, "bold"), relief=tk.FLAT, padx=20, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_history_btn = tk.Button(btn_frame, text="Réinitialiser l'Historique local", command=self.clear_history, bg="#6b7280", fg="white", relief=tk.FLAT)
        self.clear_history_btn.pack(side=tk.RIGHT, padx=5)

        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=10)

        self.status_label = tk.Label(main_frame, text="Prêt", bg="#f3f4f6", font=("Helvetica", 9, "italic"))
        self.status_label.pack(anchor=tk.W)

        # Logs
        tk.Label(main_frame, text="Journal d'activité :", bg="#f3f4f6", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        self.log_area = scrolledtext.ScrolledText(main_frame, height=15, font=("Consolas", 9), bg="#1e293b", fg="#f8fafc")
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Menu contextuel (clic droit) pour copier
        self.context_menu = tk.Menu(self.log_area, tearoff=0)
        self.context_menu.add_command(label="Copier", command=self.copy_selection)
        self.log_area.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def copy_selection(self):
        try:
            selected_text = self.log_area.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except:
            pass 

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)

    def stop_scraping(self):
        self.stop_requested = True
        self.log("🛑 Arrêt demandé... Veuillez patienter à la fin du jour en cours.")

    def clear_history(self):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        self.history = []
        self.log("♻️ Historique local réinitialisé.")

    def start_scraping(self):
        self.stop_requested = False
        start_dt = self.start_cal.get_date()
        end_dt = self.end_cal.get_date()
        
        if start_dt > end_dt:
            self.log("❌ Erreur : La date de début doit être avant la date de fin.")
            return

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        thread = threading.Thread(target=self.run_scraping_process, args=(start_dt, end_dt))
        thread.daemon = True
        thread.start()

    def run_scraping_process(self, start_date, end_date):
        try:
            if not NEWS_DB_URL:
                self.log("❌ Erreur : NEWS_DATABASE_URL est manquante.")
                self.root.after(0, self.reset_buttons)
                return
                
            conn = psycopg2.connect(NEWS_DB_URL)
            cur = conn.cursor()
            self.log("🔗 Connecté à la base de données Supabase (News).")
        except Exception as e:
            self.log(f"❌ Erreur DB : {e}")
            self.root.after(0, self.reset_buttons)
            return

        current_date = start_date
        total_days = (end_date - start_date).days + 1
        processed_days = 0

        while current_date <= end_date and not self.stop_requested:
            day_str = current_date.strftime("%Y-%m-%d")
            day_fr = current_date.strftime("%d/%m/%Y")
            
            if self.skip_scraped_var.get() and day_str in self.history:
                self.log(f"⏭️ Saut du {day_fr} (déjà fait)")
            else:
                self.log(f"🔍 Traitement du {day_fr}...")
                self.status_label.config(text=f"Traitement du {day_fr}...")
                
                self.scrape_single_day(current_date, cur, conn)
                self.save_history(day_str)

            processed_days += 1
            progress = (processed_days / total_days) * 100
            self.progress_var.set(progress)
            
            current_date += timedelta(days=1)
            time.sleep(0.3)

        cur.close()
        conn.close()
        
        if self.stop_requested:
            self.log("⏹️ Scraping arrêté par l'utilisateur.")
        else:
            self.log("🎉 Scraping terminé avec succès !")

        self.root.after(0, self.reset_buttons)

    def reset_buttons(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Prêt")

    def scrape_single_day(self, date_obj, cur, conn):
        day_str = date_obj.strftime("%Y-%m-%d")
        next_day = date_obj + timedelta(days=1)
        next_day_str = next_day.strftime("%Y-%m-%d")
        
        rss_url = f"https://news.google.com/rss/search?q=%22{CITY}%22+after:{day_str}+before:{next_day_str}&hl=fr&gl=FR&ceid=FR:fr"
        
        try:
            resp = requests.get(rss_url, timeout=10)
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            total_rss = len(items)
            
            # 1. Filtrer les articles pertinents et non présents en base
            to_process = []
            for item in items:
                title = item.find("title").text
                if CITY.lower() not in title.lower(): continue
                
                source = item.find("source").text if item.find("source") is not None else "Inconnu"
                
                cur.execute("SELECT id FROM \"Article\" WHERE title = %s AND source = %s", (title, source))
                if cur.fetchone(): continue
                
                google_link = item.find("link").text
                pub_date_str = item.find("pubDate").text
                try:
                    pub_date = parsedate_to_datetime(pub_date_str)
                except:
                    pub_date = date_obj
                
                to_process.append({
                    'title': title,
                    'source': source,
                    'google_link': google_link,
                    'pub_date': pub_date
                })

            if not to_process:
                self.log(f"   📊 RSS : {total_rss} trouvé(s) | Base : 0 ajouté(s) (déjà à jour).")
                self.log("=" * 60)
                return

            self.log(f"   🚀 Récupération parallèle de {len(to_process)} articles...")

            # 2. Fonction pour traiter un article (URL + Image)
            def fetch_data(art):
                real_url = self.decode_url(art['google_link'])
                img_url = self.get_image(real_url)
                art['real_url'] = real_url
                art['image_url'] = img_url
                return art

            # 3. Exécution parallèle (max 10 workers)
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(fetch_data, to_process))

            # 4. Insertion séquentielle
            added_count = 0
            for art in results:
                if self.stop_requested: break
                try:
                    display_title = (art['title'][:75] + '...') if len(art['title']) > 75 else art['title']
                    self.log(f"   📰 {display_title}")
                    
                    cur.execute("""
                        INSERT INTO \"Article\" (id, title, link, \"imageUrl\", source, \"publishedAt\", \"updatedAt\")
                        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (link) DO UPDATE SET \"imageUrl\" = EXCLUDED.\"imageUrl\", \"updatedAt\" = NOW()
                    """, (art['title'], art['real_url'], art['image_url'], art['source'], art['pub_date']))
                    conn.commit()
                    added_count += 1
                except:
                    conn.rollback()
            
            self.log(f"   📊 RSS : {total_rss} trouvé(s) | Base : {added_count} ajouté(s).")
            self.log("=" * 60)
            
        except Exception as e:
            self.log(f"⚠️ Erreur le {day_str}: {e}")
            self.log("=" * 60)

    def decode_url(self, url):
        if gnewsdecoder:
            try:
                d = gnewsdecoder(url)
                if d.get("status"): return d["decoded_url"]
            except: pass
        return url

    def get_image(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\\]+)["\\]', r.text, re.IGNORECASE)
                if m: return m.group(1)
        except: pass
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsScraperApp(root)
    root.mainloop()