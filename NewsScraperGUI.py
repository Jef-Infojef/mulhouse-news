import os
import json
import threading
import time
import requests
import xml.etree.ElementTree as ET
import re
import html
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
MAX_CONSECUTIVE_DECODE_ERRORS = 3

class NewsScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mulhouse Actu Manager - Scraper & History")
        self.root.geometry("800x650")
        self.root.configure(bg="#f3f4f6")
        
        self.history = self.load_history()
        self.stop_requested = False
        self.consecutive_decode_errors = 0
        
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

        tk.Label(main_frame, text="🚀 Mulhouse Actu - Scraper & History", font=("Helvetica", 16, "bold"), bg="#f3f4f6", fg="#1e293b").pack(pady=(0, 20))

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
        tk.Label(main_frame, text="Journal d\'activité :", bg="#f3f4f6", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        self.log_area = scrolledtext.ScrolledText(main_frame, height=15, font=("Consolas", 9), bg="#1e293b", fg="#f8fafc")
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Menu contextuel
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
        except: pass 

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)

    def stop_scraping(self):
        self.stop_requested = True
        self.log("🛑 Arrêt demandé... Veuillez patienter.")

    def clear_history(self):
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        self.history = []
        self.log("♻️ Historique local réinitialisé.")

    def start_scraping(self):
        self.stop_requested = False
        self.consecutive_decode_errors = 0
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
            self.log("🔗 Connecté à la base de données.")
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
                
                success = self.scrape_single_day(current_date, cur, conn)
                if not success and self.consecutive_decode_errors >= MAX_CONSECUTIVE_DECODE_ERRORS:
                    self.log(f"⛔ ARRÊT D'URGENCE : {self.consecutive_decode_errors} échecs de décodage consécutifs.")
                    self.stop_requested = True
                
                self.save_history(day_str)

            processed_days += 1
            progress = (processed_days / total_days) * 100
            self.progress_var.set(progress)
            
            current_date += timedelta(days=1)
            time.sleep(0.5)

        cur.close()
        conn.close()
        self.log("🎉 Processus terminé.")
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
            
            to_process = []
            for item in items:
                title = item.find("title").text
                if CITY.lower() not in title.lower(): continue
                source = item.find("source").text if item.find("source") is not None else "Inconnu"
                
                cur.execute("SELECT id FROM \"Article\" WHERE title = %s AND source = %s", (title, source))
                if cur.fetchone(): continue
                
                to_process.append({
                    'title': title,
                    'source': source,
                    'google_link': item.find("link").text,
                    'pub_date': parsedate_to_datetime(item.find("pubDate").text) if item.find("pubDate") is not None else date_obj
                })

            if not to_process:
                self.log(f"   📊 {day_str} : Déjà à jour.")
                return True

            self.log(f"   🚀 Traitement de {len(to_process)} articles...")

            added_count = 0
            for art in to_process:
                if self.stop_requested: break
                
                # 1. Décodage sécurisé
                real_url = self.decode_url(art['google_link'])
                if "google.com" in real_url:
                    self.consecutive_decode_errors += 1
                    self.log(f"   ⚠️ REJET : Échec décodage ({self.consecutive_decode_errors}/3)")
                    if self.consecutive_decode_errors >= MAX_CONSECUTIVE_DECODE_ERRORS:
                        return False
                    continue
                
                self.consecutive_decode_errors = 0 # Reset si succès
                
                # 2. Vérification doublon URL réelle
                cur.execute("SELECT id FROM \"Article\" WHERE link = %s", (real_url,))
                if cur.fetchone(): continue

                # 3. Enrichissement
                img_url, description = self.fetch_content_data(real_url)
                
                # 4. Insertion
                try:
                    cur.execute("""
                        INSERT INTO \"Article\" (id, title, link, \"imageUrl\", source, description, \"publishedAt\", \"updatedAt\")
                        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, NOW())
                    """, (art['title'], real_url, img_url, art['source'], description, art['pub_date']))
                    conn.commit()
                    added_count += 1
                    self.log(f"   ✅ {art['title'][:50]}...")
                except Exception as e:
                    conn.rollback()
                    self.log(f"   ❌ Erreur insertion: {e}")
            
            self.log(f"   📊 Total : {added_count} ajoutés.")
            return True
            
        except Exception as e:
            self.log(f"⚠️ Erreur le {day_str}: {e}")
            return True

    def decode_url(self, url):
        if gnewsdecoder:
            try:
                d = gnewsdecoder(url)
                if d.get("status"): return d["decoded_url"]
            except: pass
        return url

    def fetch_content_data(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        img, desc = None, None
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                # Image
                m_img = re.search(r'property=["\"]og:image["\"][^>]*content=["\"]([^"\\]+)["\\]', r.text)
                if not m_img: m_img = re.search(r'content=["\"]([^"\\]+)["\\][^>]*property=["\"]og:image["\"]', r.text)
                if m_img: img = html.unescape(m_img.group(1))
                # Description
                m_desc = re.search(r'property=["\"]og:description["\"][^>]*content=["\"]([^"\\]+)["\\]', r.text)
                if m_desc:
                    desc = html.unescape(m_desc.group(1))
                    if len(desc) > 250: desc = desc[:247] + "..."
        except: pass
        return img, desc

    def reset_buttons(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Prêt")

if __name__ == "__main__":
    root = tk.Tk()
    app = NewsScraperApp(root)
    root.mainloop()
