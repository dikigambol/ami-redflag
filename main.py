import os
import json
import re
import random
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = (os.getenv("api_key_openrouter") or os.getenv("OPENROUTER_API_KEY", "")).strip()
MODEL_NAME = "google/gemini-3.1-flash-lite"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

app = FastAPI(title="Am I The Red Flag? - AI Chat Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str
    reasoning_details: Optional[Any] = None

class ChatRequest(BaseModel):
    player_name: str
    player_gender: Optional[str] = "Laki-laki"
    chapter: int
    exchange_count: int
    messages: List[ChatMessage]
    previous_history: Optional[List[Dict[str, Any]]] = None
    custom_system_prompt: Optional[str] = None

class GenerateScenariosRequest(BaseModel):
    player_name: str
    player_gender: Optional[str] = "Laki-laki"

class EvaluateRequest(BaseModel):
    player_name: str
    player_gender: Optional[str] = "Laki-laki"
    full_history: List[Dict[str, Any]]

# Default Fallback Scenario Sets
FALLBACK_SCENARIO_SETS = [
    # Set 1: Classic
    {
        "1": {
            "chapter": 1,
            "theme": "Hubungan Personal",
            "title": "Bab 1: Hubungan Personal",
            "timeLabel": "Pagi Hari &bull; 07:45",
            "character": "Ayang",
            "initial": "A",
            "userStarts": True,
            "initialNotice": "Semalam kamu menghilang tanpa kabar dan chat terakhirnya cuma kamu read. Pagi ini kamu yang harus memulai obrolan duluan.",
            "initialMessage": None,
            "situation_summary": "Pasangan kesal karena di-ghosting / ditinggal tidur semalaman tanpa kabar.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 2: Krisis Profesional",
            "transitionDesc": "Jam makan siang baru saja berakhir. Di tengah persiapan mendesak menjelang rapat dewan direksi, rekan kerja mejamu menghubungimu dalam keadaan panik luar biasa.",
            "system_prompt": (
                "Kamu adalah 'Ayang', kekasih {player_name}. Kamu perempuan muda yang cerdas, intuitif, berpendirian, dan peka terhadap pola komunikasi pasangan.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Semalam {player_name} menghilang begitu saja tanpa kabar (chat terakhirmu di-read doang atau ditinggal tidur tanpa pamit). Pagi ini dia baru saja menghubungimu duluan. Kamu masih kesal, jengkel, dan butuh penjelasan yang masuk akal.\n\n"
                "ATURAN LOGIKA & KONSISTENSI UTAMA:\n"
                "1. RESPON LANGSUNG PESAN TERAKHIR: Tanggapi tepat apa yang baru saja {player_name} katakan.\n"
                "2. BACA CHAT HISTORY DENGAN TELITI: Jangan mengulang pertanyaan yang sudah dia jawab.\n"
                "3. PERKEMBANGAN EMOSI: Jika dia sok manis, tanggapi dingin dan sinis. Jika dia tulus minta maaf dan solutif, mulai melunak perlahan. Jika defensif/playing victim, balas lebih tegas.\n"
                "4. GAYA BAHASA: Bahasa chat WhatsApp perempuan muda Indonesia yang natural ('aku', 'kamu', 'sih', 'deh', 'kan', 'emang'). Singkat 1-3 kalimat.\n"
                "5. DILARANG KERAS memakai narasi bertanda bintang seperti *menghela napas*."
            )
        },
        "2": {
            "chapter": 2,
            "theme": "Krisis Profesional",
            "title": "Bab 2: Krisis Profesional",
            "timeLabel": "Siang Hari &bull; 11:30",
            "character": "Budi (Rekan Kerja)",
            "initial": "B",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Gawat bro... Gue gak sengaja numpahin kopi terus file master proposal tender tim kita kehapus permanen dari laptop gue, padahal 30 menit lagi meeting sama direksi! Lo bisa bantuin gue ngomong ke bos gak plis?",
            "situation_summary": "Rekan kerja panik menumpahkan kopi dan file tender hilang 30 menit sebelum presentasi direksi.",
            "transitionTime": "4 Jam Kemudian",
            "transitionTitle": "Bab 3: Batasan Sosial",
            "transitionDesc": "Pukul 17:30 sore. Tubuhmu sudah kelelahan setelah menyelesaikan serangkaian deadline kerja. Tiba-tiba salah seorang teman dekatmu mengirimkan pesan mendesak.",
            "system_prompt": (
                "Kamu adalah 'Budi', rekan kerja satu tim {player_name} di kantor. Kamu panik luar biasa.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "30 menit lagi sebelum presentasi tender di depan dewan direksi. Kamu menumpahkan kopi dan proposal tender tim terhapus. Kamu memohon bantuan {player_name}.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung solusi atau teguran dari {player_name}.\n"
                "2. Jika dia solutif, tanggapi dengan harapan dan lega. Jika dia lepas tangan ('itu salah lo'), tunjukkan kekecewaan mendalam.\n"
                "3. Bahasa chat rekan kerja sebaya Jakarta ('bro', 'lo', 'gue', 'anjir', 'plis'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "3": {
            "chapter": 3,
            "theme": "Batasan Sosial",
            "title": "Bab 3: Batasan Sosial",
            "timeLabel": "Sore Hari &bull; 17:30",
            "character": "Dimas (Teman)",
            "initial": "D",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Bro! Pokoknya lu WAJIB ikut nongkrong sore ini, anak-anak udah pada kumpul nih. Gak ada alesan capek atau kerjaan, masa lu gak solid banget sih?!",
            "situation_summary": "Teman nongkrong memaksa kumpul dengan guilt-trip saat kamu kelelahan kerja.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 4: Integritas Etika",
            "transitionDesc": "Pukul 20:30 malam. Kamu sedang bersantai di rumah setelah seharian beraktivitas. Tiba-tiba masuk notifikasi WhatsApp dari admin toko online tempat kamu membeli gadget...",
            "system_prompt": (
                "Kamu adalah 'Dimas', sahabat lama {player_name}. Kamu suka guilt-tripping jika teman menolak diajak kumpul.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Sore ini kamu kumpul di kafe dan memaksa {player_name} datang walau dia capek.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung alasan {player_name}. Patahkan alasannya secara santai.\n"
                "2. Gunakan tahapan: guilt-trip ('kemarin pas lo butuh gue temenin'), tekanan sosial ('anak-anak nanyain lo'), hingga godaan.\n"
                "3. Jika dia tetap tegas dan konsisten menolak: Mulai mengalah dengan nada bercanda.\n"
                "4. Slang tongkrongan ('lu', 'gue', 'bro', 'cuy'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "4": {
            "chapter": 4,
            "theme": "Integritas Etika",
            "title": "Bab 4: Integritas Etika",
            "timeLabel": "Malam Hari &bull; 20:30",
            "character": "Clarissa (Admin Toko)",
            "initial": "C",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Malam Kak, maaf banget ya ganggu jam istirahatnya 🙏 Paket pesanan dari toko kami kan baru sampai sore tadi ya Kak? Staf gudang kami yang baru magang panik banget dan nangis, katanya pas packing tadi siang gak sengaja masukin 2 unit barang ke dalam kardus Kakak... Boleh tolong dicek kardus paketnya Kak? 🥺",
            "situation_summary": "Admin toko cemas karena staf magang salah memasukkan 2 gadget berharga ke dalam paketmu.",
            "transitionTime": "Evaluasi Akhir",
            "transitionTitle": "Menganalisis Karakter",
            "transitionDesc": "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
            "system_prompt": (
                "Kamu adalah 'Clarissa', CS toko gadget online. Sangat sopan dan cemas karena audit stok sore ini bermasalah.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Anak magang salah packing mengirim 2 unit gadget ke {player_name}. Jika tidak kembali, staf magang harus ganti rugi.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Jika jujur & mau mengembalikan: Sangat terharu dan siap menanggung semua ongkos kirim penjemputan.\n"
                "2. Jika berbohong / berkelit: Ingatkan dengan santun mengenai bukti rekaman CCTV dan data berat timbangan ekspedisi.\n"
                "3. Bahasa CS ramah e-commerce ('Kak', 'Kakak', 'terima kasih banyak Kak 🙏'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        }
    },
    # Set 2: Campus & Social Circles
    {
        "1": {
            "chapter": 1,
            "theme": "Hubungan Personal",
            "title": "Bab 1: Hubungan Personal",
            "timeLabel": "Pagi Hari &bull; 08:15",
            "character": "Nabila (Gebetan)",
            "initial": "N",
            "userStarts": True,
            "initialNotice": "Semalam kamu mengunggah story makan malam bersama teman-teman, sementara chat Nabila baru kamu balas 4 jam kemudian secara singkat. Pagi ini suasananya terasa canggung.",
            "initialMessage": None,
            "situation_summary": "Gebetan bersikap pasif-agresif dan dingin karena kamu slow respon semalam saat asyik nongkrong.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 2: Krisis Profesional",
            "transitionDesc": "Siang hari di kampus. Menjelang batas akhir pengumpulan proyek tim akhir semester, salah satu anggota tim mengirimkan pesan darurat.",
            "system_prompt": (
                "Kamu adalah 'Nabila', gebetan {player_name} yang sedang dalam tahap pendekatan (PDKT). Kamu cerdas, peka, dan agak gengsian.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Semalam kamu chat {player_name} menanyakan kabarnya, tapi dia baru balas 4 jam kemudian dengan alasan 'capek banget langsung tidur'. Padahal 30 menit setelahnya dia terlihat aktif di story Instagram temannya. Pagi ini dia menghubungimu duluan.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung pesan pembukanya dengan nada dingin, pasif-agresif ('Oh masih inget balas chat? Kirain masih sibuk banget').\n"
                "2. Jika dia jujur dan minta maaf tulus tanpa alasan klise: Perlahan turunkan gengsi dan bicarakan secara dewasa.\n"
                "3. Jika dia manipulatif atau menyangkal: Sindir dengan fakta story yang kamu lihat.\n"
                "4. Bahasa chat anak muda santai ('kamu', 'aku', 'sih', 'ya'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "2": {
            "chapter": 2,
            "theme": "Krisis Profesional",
            "title": "Bab 2: Krisis Profesional",
            "timeLabel": "Siang Hari &bull; 12:45",
            "character": "Kevin (Rekan Tim)",
            "initial": "K",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Bro {player_name}, tolongin gue banget plis! Nama gue jangan dicoret dari laporan proyek yang mau dikumpulin ke dosen jam 1 ini ya. Gue semalam ketiduran parah jadi belum sempat ngerjain bagian gue...",
            "situation_summary": "Rekan satu tim proyek tidak mengerjakan bagiannya dan memohon agar namanya tetap dimasukkan.",
            "transitionTime": "4 Jam Kemudian",
            "transitionTitle": "Bab 3: Batasan Sosial",
            "transitionDesc": "Sore hari pukul 17:30. Setelah urusan kuliah selesai, ponselmu berdering dengan rentetan pesan mendesak dari teman tongkrongan lamamu.",
            "system_prompt": (
                "Kamu adalah 'Kevin', teman satu kelompok proyek akhir {player_name}. Kamu santai tapi tidak bertanggung jawab dan sering menunda tugas.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Tinggal 45 menit sebelum deadline pengumpulan laporan proyek ke dosen. Kamu sama sekali belum menyentuh bagian analisismu dan memohon agar {player_name} tetap mencantumkan namamu.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Respon tepat apa yang dikatakan {player_name}.\n"
                "2. Jika dia menolak: Tawarkan imbalan (bayarin makan/ongkos) atau gunakan alasan iba (nilai ini penentu kelulusan).\n"
                "3. Jika dia tegas menuntut kontribusi instan: Coba nego bagian mana yang bisa kamu selesaikan dalam 30 menit.\n"
                "4. Gaya bahasa mahasiswa akrab ('bro', 'lo', 'gue', 'plis'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "3": {
            "chapter": 3,
            "theme": "Batasan Sosial",
            "title": "Bab 3: Batasan Sosial",
            "timeLabel": "Sore Hari &bull; 17:30",
            "character": "Rendy (Teman Lama)",
            "initial": "R",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Bro {player_name}! Lo ada dana nganggur 1,5 juta gak? Penting banget hari ini sebelum jam 7 malam, gue kepepet jatuh tempo pinjol. Besok lusa langsung gue balikin utuh sumpah!",
            "situation_summary": "Teman mendesak meminjam uang darurat untuk menutup pinjol dengan janji manis.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 4: Integritas Etika",
            "transitionDesc": "Malam hari pukul 20:45. Kamu baru saja tiba di rumah dan mendapati paket ekspedisi berada di depan pintu pagar.",
            "system_prompt": (
                "Kamu adalah 'Rendy', teman SMA {player_name}. Kamu sedang terlilit hutang pinjaman online dan panik diteror penagih.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Kamu mendesak meminjam 1,5 juta ke {player_name}. Sebenarnya kamu belum tahu kapan pasti bisa mengembalikannya.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung respon penolakan atau tawaran {player_name}.\n"
                "2. Jika dia menolak: Mainkan kartu iba ('gue gak ada tempat minjam lagi bro, lo temen terbaik gue').\n"
                "3. Jika dia minta jaminan atau menolak tegas: Mulai pasrah namun tetap berharap dipinjamkan sebagian.\n"
                "4. Gaya bahasa tongkrongan mendesak ('bro', 'cuy', 'lo', 'gue'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "4": {
            "chapter": 4,
            "theme": "Integritas Etika",
            "title": "Bab 4: Integritas Etika",
            "timeLabel": "Malam Hari &bull; 21:00",
            "character": "Pak Slamet (Kurir Paket)",
            "initial": "S",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Malam Mas {player_name}, mohon maaf mengganggu malam-malam 🙏 Tadi sore saya taruh paket di pagar rumah Mas. Ternyata saya salah lihat nomor rumah, itu paket smartwatch mahal milik tetangga blok sebelah Mas. Apakah paketnya masih utuh dan belum dibuka Mas? 🥺",
            "situation_summary": "Kurir ekspedisi salah mengantar paket barang elektronik mahal tetangga ke rumahmu.",
            "transitionTime": "Evaluasi Akhir",
            "transitionTitle": "Menganalisis Karakter",
            "transitionDesc": "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
            "system_prompt": (
                "Kamu adalah 'Pak Slamet', kurir ekspedisi yang gajinya pas-pasan dan sangat ketakutan karena salah meletakkan paket barang elektronik mahal.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Paket smartwatch mahal milik tetangga tertinggal di pagar rumah {player_name}. Jika barang hilang, kamu harus mengganti rugi sebulan gaji.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Jika {player_name} jujur mengakui dan mengembalikan: Ucapkan terima kasih dengan penuh haru dan doakan kebaikan untuknya.\n"
                "2. Jika dia berdalih tidak ada atau mengaku sudah hilang: Mohon dengan sangat sambil menyebutkan bukti foto resi saat barang diletakkan di pagar.\n"
                "3. Bahasa kurir sopan dan santun ('Mas', 'terima kasih banyak Mas 🙏'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        }
    },
    # Set 3: Modern Workplace & Lifestyle
    {
        "1": {
            "chapter": 1,
            "theme": "Hubungan Personal",
            "title": "Bab 1: Hubungan Personal",
            "timeLabel": "Pagi Hari &bull; 08:30",
            "character": "Tiara (Mantan)",
            "initial": "T",
            "userStarts": True,
            "initialNotice": "Kemarin kamu tanpa sengaja menemukan jaket hoodie favorit Tiara yang tertinggal di lemari kamarmu sejak beberapa bulan lalu. Kamu memutuskan menghubunginya pagi ini.",
            "initialMessage": None,
            "situation_summary": "Mantan pacar memanfaatkan urusan barang tertinggal untuk menguji batas emosimu dan memancing nostalgia.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 2: Krisis Profesional",
            "transitionDesc": "Pukul 13:00 di kantor startup. Di tengah persiapan pitch deck klien besar sore ini, seorang rekan kerja mengirimkan pesan mencurigakan.",
            "system_prompt": (
                "Kamu adalah 'Tiara', mantan kekasih {player_name}. Hubungan kalian selesai beberapa bulan lalu, tapi kamu masih penasaran dan suka memancing reaksinya.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Pagi ini {player_name} chat kamu duluan untuk mengabarkan hoodie kamu yang tertinggal.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung chat pembukanya. Gunakan kesempatan ini untuk menyelipkan nostalgia atau pertanyaan pancingan ('Tumben inget aku, kirain udah kamu buang', 'Kapan nih mau balikin langsung sambil ngopi?').\n"
                "2. Jika dia menjaga batasan tegas & profesional: Hormati batasannya namun beri sedikit komentar satir.\n"
                "3. Jika dia tergoda dan baper: Tarik ulur perhatiannya.\n"
                "4. Bahasa chat santai ('kamu', 'aku', 'sih', 'deh'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "2": {
            "chapter": 2,
            "theme": "Krisis Profesional",
            "title": "Bab 2: Krisis Profesional",
            "timeLabel": "Siang Hari &bull; 13:15",
            "character": "Adrian (Rekan Startup)",
            "initial": "A",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "{player_name}, slide market research kompetitor yang barusan gue masukin ke pitch deck sebenarnya gue ambil plek-ketiplek dari dokumen rahasia kantor lama gue. Bos minta dipresentasikan jam 3 ini. Lo diem aja ya, anggap ini riset tim kita sendiri.",
            "situation_summary": "Rekan kerja menjiplak data rahasia kompetitor dan memintamu diam saat presentasi.",
            "transitionTime": "4 Jam Kemudian",
            "transitionTitle": "Bab 3: Batasan Sosial",
            "transitionDesc": "Pukul 18:00 sore. Pekerjaan baru saja usai ketika notifikasi grup circle pertemanan membanjiri layar ponselmu.",
            "system_prompt": (
                "Kamu adalah 'Adrian', rekan kerja satu divisi {player_name} di kantor startup. Kamu ambisius dan suka mengambil jalan pintas berisiko.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Kamu menggunakan data rahasia kantor lamamu untuk pitch deck sore ini dan mendesak {player_name} untuk tutup mulut demi kesuksesan bersama.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung penolakan atau saran integritas dari {player_name}.\n"
                "2. Jika dia menolak: Tekankan bahwa ini demi bonus tim dan startup butuh klien ini.\n"
                "3. Jika dia mendesak mengubah data: Tunjukkan keraguan karena waktu tinggal sedikit, minta dia membantu mengganti dengan data aman.\n"
                "4. Bahasa chat kantor Jakarta ('bro', 'lo', 'gue', 'santai aja kali'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "3": {
            "chapter": 3,
            "theme": "Batasan Sosial",
            "title": "Bab 3: Batasan Sosial",
            "timeLabel": "Sore Hari &bull; 18:00",
            "character": "Gani (Circle Teman)",
            "initial": "G",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Woy {player_name}! Kita fix booking villa private di Bali buat liburan long weekend besok lusa. Patungannya kena 3 juta per orang ya, gue tunggu transferannya malam ini juga biar gak hangus!",
            "situation_summary": "Circle teman memaksa ikut patungan liburan mewah mendadak yang melebihi budgetmu.",
            "transitionTime": "3 Jam Kemudian",
            "transitionTitle": "Bab 4: Integritas Etika",
            "transitionDesc": "Pukul 21:00 malam. Kamu sedang bersantai di kedai kopi dekat rumah ketika kasir mengirimkan pesan ke kontak nomormu.",
            "system_prompt": (
                "Kamu adalah 'Gani', teman satu circle nongkrong {player_name} yang konsumtif dan suka mengambil keputusan sepihak untuk rombongan.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Kamu mendadak meminta patungan 3 juta untuk villa mewah tanpa meminta persetujuan {player_name} terlebih dahulu.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Tanggapi langsung alasan finansial atau penolakan {player_name}.\n"
                "2. Jika dia menolak: Lakukan peer pressure ('Masa lo gak ikut sih, semua udah setuju tinggal nunggu lo doang, jangan pelit sama diri sendiri lah').\n"
                "3. Jika dia tetap tegas mempertahankan batasan finansialnya: Akui ketegasannya walau sedikit menyindir.\n"
                "4. Slang tongkrongan modern ('woy', 'cuy', 'lo', 'gue'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        },
        "4": {
            "chapter": 4,
            "theme": "Integritas Etika",
            "title": "Bab 4: Integritas Etika",
            "timeLabel": "Malam Hari &bull; 21:15",
            "character": "Maya (Kasir Kafe)",
            "initial": "M",
            "userStarts": False,
            "initialNotice": None,
            "initialMessage": "Halo Kak {player_name}, maaf banget chat malam-malam 🙏 Tadi sore Kakak bayar bill kafe tunai kan ya? Pas saya rekap kas kasir barusan, ada selisih uang 100 ribu yang keliru saya kembalikan berlebih ke Kakak... Boleh tolong dicek dompetnya Kak? Soalnya kalau nombok dipotong dari gaji saya 🥺",
            "situation_summary": "Kasir kafe keliru memberikan kembalian tunai berlebih sebesar 100 ribu dan memohon kejujuranmu.",
            "transitionTime": "Evaluasi Akhir",
            "transitionTitle": "Menganalisis Karakter",
            "transitionDesc": "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
            "system_prompt": (
                "Kamu adalah 'Maya', staf kasir kafe yang baru bekerja sebulan. Kamu cemas karena pembukuan kasir malam ini tekor 100 ribu.\n\n"
                "LATAR BELAKANG SITUASI:\n"
                "Kamu sadar telah salah memberikan uang kembalian 100 ribu berlebih kepada {player_name} saat kondisi kafe ramai tadi sore.\n\n"
                "ATURAN LOGIKA:\n"
                "1. Jika {player_name} jujur dan bersedia mengembalikan / transfer balik: Sangat berterima kasih dan bersyukur.\n"
                "2. Jika dia berdalih sudah lupa atau tidak mau repot: Sampaikan dengan sopan rincian nomor struk pembayaran dan memohon pengertiannya.\n"
                "3. Bahasa kasir muda sopan ('Kak', 'Kakak', 'terima kasih banyak ya Kak 🙏'). 1-3 kalimat, tanpa tanda bintang narasi."
            )
        }
    }
]

def call_openrouter(messages: list, temperature: float = 0.55) -> tuple:
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY tidak ditemukan di environment (.env)")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Am I The Red Flag Game",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "reasoning": {"enabled": True}
    }

    try:
        res = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=35)
        res.raise_for_status()
        data = res.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "") or ""
        reasoning_details = msg.get("reasoning_details")
        return content.strip(), reasoning_details
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal memanggil OpenRouter: {str(e)}")

def get_fallback_scenarios(player_name: str) -> Dict[str, Any]:
    selected_set = random.choice(FALLBACK_SCENARIO_SETS)
    # Deep copy & replace player_name
    result = {}
    for k, v in selected_set.items():
        ch_copy = dict(v)
        if ch_copy.get("initialNotice"):
            ch_copy["initialNotice"] = ch_copy["initialNotice"].format(player_name=player_name)
        if ch_copy.get("initialMessage"):
            ch_copy["initialMessage"] = ch_copy["initialMessage"].format(player_name=player_name)
        if ch_copy.get("system_prompt"):
            ch_copy["system_prompt"] = ch_copy["system_prompt"].format(player_name=player_name)
        result[k] = ch_copy
    return result

@app.post("/api/generate-scenarios")
@app.post("/generate-scenarios")
async def generate_scenarios_handler(req: GenerateScenariosRequest):
    player = req.player_name.strip() or "Kamu"
    gender = req.player_gender or "Laki-laki"
    
    prompt = f"""Kamu adalah perancang narasi game psikologis 'Am I The Red Flag?'.
Rancanglah 4 skenario obrolan WhatsApp yang segar, dinamis, realistis, dan bervariasi untuk pemain bernama '{player}' (Jenis Kelamin: {gender}).
PENTING: Sesuaikan dinamika relasi, peran karakter, dan panggilan sosial (Mas/Mbak/Kak/Bro/Sis) dengan jenis kelamin pemain ({gender}).
- Jika pemain Laki-laki: Bab 1 bisa berupa pacar perempuan, gebetan cewek, atau adik perempuan.
- Jika pemain Perempuan: Bab 1 bisa berupa pacar laki-laki, gebetan cowok, atau saudara laki-laki.
- Bab 2 s/d 4 sesuaikan interaksi sosialnya secara natural khas pergaulan anak muda Indonesia.
Setiap sesi permainan harus memiliki karakter dan konflik berbeda yang memicu respons moral/sosial.

4 PILAR BAB WAJIB:
- Bab 1 (Pagi): Hubungan Personal / Asmara / Keluarga Dekat (contoh: pasangan ngambek, gebetan baru pasif-agresif karena slow respon, mantan mendadak chat, saudara merusak barang tanpa izin, dll).
- Bab 2 (Siang): Krisis Profesional / Dunia Kerja / Tim (contoh: rekan kerja panik file tender terhapus sebelum meeting, rekan tim ketahuan plagiasi data klien 1 jam sebelum deadline, teman kelompok skripsi mau numpang nama, dll).
- Bab 3 (Sore): Batasan Sosial / Peer Pressure / Tongkrongan (contoh: sahabat memaksa nongkrong dengan guilt-trip saat lelah, teman pinjam uang besar mendadak, teman mendesak ikut membicarakan/menjatuhkan orang lain, patungan pesta mewah di luar budget, dll).
- Bab 4 (Malam): Integritas Etika / Kejujuran / Moral (contoh: admin toko online salah kirim 2 barang, driver ojol kelebihan uang kembalian belanja bulanan, kasir lupa scan barang belanjaan berharga, paket tetangga salah antar, dll).

ATURAN OUTPUT:
WAJIB HANYA berupa JSON valid tanpa markdown codeblocks (tanpa ```json) dengan struktur objek persis berikut:
{{
  "1": {{
    "chapter": 1,
    "theme": "Hubungan Personal",
    "title": "Bab 1: Hubungan Personal",
    "timeLabel": "Pagi Hari &bull; 08:15",
    "character": "Nama Karakter (Relasi)",
    "initial": "Satu Huruf Inisial",
    "userStarts": true,
    "initialNotice": "Penjelasan situasi singkat mengapa user harus membuka chat duluan kepada karakter...",
    "initialMessage": null,
    "situation_summary": "Ringkasan konflik 1 kalimat",
    "transitionTime": "3 Jam Kemudian",
    "transitionTitle": "Bab 2: Krisis Profesional",
    "transitionDesc": "Deskripsi transisi suasana menuju bab 2...",
    "system_prompt": "Kamu adalah '[Nama Karakter]', [relasi] {player}. [Sifat & emosi saat ini].\\n\\nLATAR BELAKANG SITUASI:\\n[Latar belakang masalah].\\n\\nATURAN LOGIKA & KONSISTENSI UTAMA:\\n1. RESPON LANGSUNG PESAN TERAKHIR: Tanggapi tepat apa yang dikatakan {player}.\\n2. BACA CHAT HISTORY DENGAN TELITI.\\n3. GAYA BAHASA: Bahasa chat WhatsApp Indonesia natural 1-3 kalimat.\\n4. DILARANG KERAS menggunakan tanda bintang narasi seperti *menghela napas*."
  }},
  "2": {{
    "chapter": 2,
    "theme": "Krisis Profesional",
    "title": "Bab 2: Krisis Profesional",
    "timeLabel": "Siang Hari &bull; 12:45",
    "character": "Nama Karakter (Relasi)",
    "initial": "Satu Huruf Inisial",
    "userStarts": false,
    "initialNotice": null,
    "initialMessage": "Chat pembuka pertama dari karakter yang panik/mendesak...",
    "situation_summary": "Ringkasan situasi 1 kalimat",
    "transitionTime": "4 Jam Kemudian",
    "transitionTitle": "Bab 3: Batasan Sosial",
    "transitionDesc": "Deskripsi transisi...",
    "system_prompt": "Kamu adalah '[Nama Karakter]', [relasi] {player}... (instruksi lengkap, gaya bahasa chat kerja 1-3 kalimat, tanpa tanda bintang narasi)"
  }},
  "3": {{
    "chapter": 3,
    "theme": "Batasan Sosial",
    "title": "Bab 3: Batasan Sosial",
    "timeLabel": "Sore Hari &bull; 17:30",
    "character": "Nama Karakter (Relasi)",
    "initial": "Satu Huruf Inisial",
    "userStarts": false,
    "initialNotice": null,
    "initialMessage": "Chat pembuka pertama yang mendesak/memaksa...",
    "situation_summary": "Ringkasan situasi 1 kalimat",
    "transitionTime": "3 Jam Kemudian",
    "transitionTitle": "Bab 4: Integritas Etika",
    "transitionDesc": "Deskripsi transisi...",
    "system_prompt": "Kamu adalah '[Nama Karakter]', [relasi] {player}... (instruksi guilt-trip / desakan teman sebaya, gaya bahasa tongkrongan 1-3 kalimat, tanpa tanda bintang narasi)"
  }},
  "4": {{
    "chapter": 4,
    "theme": "Integritas Etika",
    "title": "Bab 4: Integritas Etika",
    "timeLabel": "Malam Hari &bull; 21:00",
    "character": "Nama Karakter (Relasi)",
    "initial": "Satu Huruf Inisial",
    "userStarts": false,
    "initialNotice": null,
    "initialMessage": "Chat pembuka pertama mengenai barang/uang/kejujuran...",
    "situation_summary": "Ringkasan situasi 1 kalimat",
    "transitionTime": "Evaluasi Akhir",
    "transitionTitle": "Menganalisis Karakter",
    "transitionDesc": "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
    "system_prompt": "Kamu adalah '[Nama Karakter]', [relasi] {player}... (instruksi respon jika user jujur vs bohong vs minta imbalan, 1-3 kalimat, tanpa tanda bintang narasi)"
  }}
}}"""

    try:
        raw_output, _ = call_openrouter([{"role": "user", "content": prompt}], temperature=0.75)
        cleaned = re.sub(r"^```json\s*", "", raw_output.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)
        
        parsed = json.loads(cleaned)
        # Validate that all 4 chapters exist
        if all(str(i) in parsed for i in [1, 2, 3, 4]):
            for i in [1, 2, 3, 4]:
                ch = parsed[str(i)]
                ch["chapter"] = i
                if not ch.get("initial"):
                    ch["initial"] = (ch.get("character") or "B")[0].upper()
            return {"status": "success", "source": "ai", "chapters": parsed}
    except Exception as e:
        print(f"[GenerateScenarios] OpenRouter gagal/error ({str(e)}), memakai fallback preset.")
    
    fallback = get_fallback_scenarios(player)
    return {"status": "success", "source": "fallback", "chapters": fallback}

@app.post("/api/chat")
@app.post("/chat")
async def chat_handler(req: ChatRequest):
    gender_info = req.player_gender or "Laki-laki"
    sapaan_default = "Mas" if gender_info == "Laki-laki" else "Mbak"

    # Gunakan custom_system_prompt dari skenario dinamis jika ada
    if req.custom_system_prompt:
        system_text = req.custom_system_prompt.replace("{player_name}", req.player_name or "Kamu")
        system_text = system_text.replace("{player_gender}", gender_info)
    else:
        fallback_set = FALLBACK_SCENARIO_SETS[0]
        ch_config = fallback_set.get(str(req.chapter), fallback_set["1"])
        system_text = ch_config["system_prompt"].format(
            player_name=req.player_name or "Kamu",
            exchange_count=req.exchange_count
        )

    # Tambahkan memori bab-bab sebelumnya jika ada
    memory_context = ""
    if req.previous_history:
        summary_lines = []
        for prev in req.previous_history:
            ch_title = prev.get("chapter_title", f"Bab {prev.get('chapter', '?')}")
            char = prev.get("character", "Seseorang")
            sit = prev.get("situation_summary", "")
            msgs = prev.get("messages", [])
            dialog_str = " -> ".join([f"[{m.get('role')}]: {m.get('content')}" for m in msgs])
            sit_desc = f" (Masalah: {sit})" if sit else ""
            summary_lines.append(f"- {ch_title} dengan {char}{sit_desc}: {dialog_str}")

        memory_context = (
            "\n\n[MEMORI HARI INI - KEJADIAN PADA BAB SEBELUMNYA]:\n"
            f"Hari ini {req.player_name} telah melewati skenario berikut:\n"
            + "\n\n".join(summary_lines) + "\n\n"
            "Instruksi Memori: Ini adalah rangkaian hari yang sama. Jika pengguna mengungkit kejadian sebelumnya, sambunglah secara kontekstual!"
        )

    # Identitas gender pengguna
    gender_instruction = (
        f"\n\n[IDENTITAS LAWAN BICARA]:\n"
        f"Lawan bicaramu adalah {req.player_name}, seorang {gender_info}. "
        f"Gunakan sapaan dan gaya komunikasi yang natural dan sesuai ({sapaan_default} / Kak / Bro / Sis / nama)."
    )

    # Instruksi penegasan agar AI fokus ke pesan terakhir user
    current_focus_instruction = (
        "\n\n[PANDUAN UTAMA]:\n"
        "BACA SELURUH RIWAYAT CHAT DI ATAS. Responmu WAJIB langsung menjawab dan menyambung pesan TERAKHIR dari user. "
        "Jangan keluar konteks obrolan. Jangan mengulang pertanyaan yang sudah dijawab. Berikan balasan realistis chat WhatsApp (1-3 kalimat)."
    )

    full_system_prompt = system_text + gender_instruction + memory_context + current_focus_instruction

    openrouter_messages = [{"role": "system", "content": full_system_prompt}]
    for m in req.messages:
        item = {"role": m.role, "content": m.content}
        if m.reasoning_details is not None:
            item["reasoning_details"] = m.reasoning_details
        openrouter_messages.append(item)

    raw_reply, reasoning_details = call_openrouter(openrouter_messages, temperature=0.55)
    cleaned_reply = raw_reply.replace("[SELESAI]", "").strip()

    # Sarankan selesai jika sudah minimal 3 interaksi bolak-balik
    suggest_end = req.exchange_count >= 3

    return {
        "reply": cleaned_reply,
        "reasoning_details": reasoning_details,
        "suggest_end": suggest_end,
        "exchange_count": req.exchange_count
    }

@app.post("/api/evaluate")
@app.post("/evaluate")
async def evaluate_handler(req: EvaluateRequest):
    gender_info = req.player_gender or "Laki-laki"
    history_summary = []
    scenarios_overview = []
    for idx, item in enumerate(req.full_history, 1):
        ch_title = item.get("chapter_title", f"Bab {item.get('chapter', idx)}")
        char_name = item.get("character", "Lawan Bicara")
        situation = item.get("situation_summary", "")
        dialog_lines = []
        for msg in item.get("messages", []):
            sender = req.player_name if msg.get("role") == "user" else char_name
            dialog_lines.append(f"{sender}: {msg.get('content')}")
        sit_info = f" (Situasi: {situation})" if situation else ""
        history_summary.append(f"### {ch_title} - {char_name}{sit_info}:\n" + "\n".join(dialog_lines))
        scenarios_overview.append(f"{idx}. {ch_title} (Menghadapi {char_name}): {situation or 'Konflik sosial'}")

    full_conversation_text = "\n\n".join(history_summary)
    overview_text = "\n".join(scenarios_overview)

    system_prompt = (
        "Kamu adalah psikolog perilaku komunikasi klinis dan analis karakter hubungan yang sangat tajam, cerdas, berwawasan, dan objektif. "
        f"Analisis seluruh riwayat percakapan pengguna bernama '{req.player_name}' (seorang {gender_info}) saat menghadapi 4 skenario konflik sosial berikut hari ini:\n\n"
        f"{overview_text}\n\n"
        "KRITERIA PENILAIAN SKOR RED FLAG (0 - 100):\n"
        "- 0 - 35 = Green Flag (Dewasa, bertanggung jawab, jujur, mampu menetapkan batasan sehat, empati tinggi)\n"
        "- 36 - 69 = Yellow Flag (Situasional, kadang cari aman, sedikit defensif tapi masih punya kompas moral)\n"
        "- 70 - 100 = Red Flag (Toxic, manipulatif, gaslighting, egois, berbohong demi keuntungan pribadi, lepas tanggung jawab)\n\n"
        "PEDOMAN KONTEN LAPORAN:\n"
        "- 'julukan': Berikan julukan psikologis yang cerdas, unik, satir tapi akurat (contoh: 'Manipulator Halus Berwajah Malaikat', 'Pakar Cari Aman Internasional', 'Benteng Pertahanan Tanpa Celah', 'Partner Idaman Generasi Emas', 'Pahlawan Empati Tanpa Pamrih', 'Diplomat Netral Anti-Drama').\n"
        "- 'analisis': Tulis 2 paragraf padat, mengalir, dan mendalam. Soroti bukti konkret bagaimana dia merespons di setiap bab (evaluasi tindakan nyata pengguna terhadap lawan bicaranya di bab 1, 2, 3, dan 4).\n"
        "- 'saran': 1-2 kalimat saran bijak, bernas, dan aplikatif untuk pengembangan dirinya.\n"
        "- 'dimensi': Berikan persentase 0-100 yang akurat untuk: manipulasi, empati, kebohongan, dan kesabaran.\n\n"
        "ATURAN OUTPUT: WAJIB HANYA berupa JSON valid tanpa backtick markdown (tanpa ```json) dengan struktur:\n"
        "{\n"
        '  "skor_red_flag": integer (0-100),\n'
        '  "kategori": "Red Flag" | "Yellow Flag" | "Green Flag",\n'
        '  "julukan": "string",\n'
        '  "analisis": "string",\n'
        '  "saran": "string",\n'
        '  "dimensi": {\n'
        '    "manipulasi": integer (0-100),\n'
        '    "empati": integer (0-100),\n'
        '    "kebohongan": integer (0-100),\n'
        '    "kesabaran": integer (0-100)\n'
        "  }\n"
        "}"
    )

    openrouter_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Berikut transkrip lengkap 4 bab percakapan {req.player_name}:\n\n{full_conversation_text}"}
    ]

    raw_eval, _ = call_openrouter(openrouter_messages, temperature=0.6)

    # Bersihkan jika ada markdown codeblock
    cleaned_json_str = re.sub(r"^```json\s*", "", raw_eval.strip(), flags=re.IGNORECASE)
    cleaned_json_str = re.sub(r"\s*```$", "", cleaned_json_str.strip())
    match = re.search(r"(\{.*\})", cleaned_json_str, re.DOTALL)
    if match:
        cleaned_json_str = match.group(1)

    try:
        eval_data = json.loads(cleaned_json_str)
    except Exception:
        eval_data = {
            "skor_red_flag": 55,
            "kategori": "Yellow Flag",
            "julukan": "Diplomat Ambivalen",
            "analisis": f"Respon {req.player_name} menunjukkan pola situasional antara menjaga citra diri dan mencari solusi aman. Dalam beberapa situasi terbukti mampu berempati, namun masih terdapat kecenderungan defensif saat terpojok.",
            "saran": "Kembangkan kejujuran emosional secara konsisten tanpa harus takut dinilai buruk oleh orang lain.",
            "dimensi": {
                "manipulasi": 45,
                "empati": 65,
                "kebohongan": 35,
                "kesabaran": 60
            }
        }

    return eval_data

try:
    os.makedirs("static", exist_ok=True)
    os.makedirs("static/css", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)
except Exception:
    pass

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")
